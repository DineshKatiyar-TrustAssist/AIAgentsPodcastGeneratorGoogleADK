"""
AI Agents Podcast Generator using Google ADK.
Converts research papers into engaging podcast conversations.
"""
from google.adk.agents import Agent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
import PyPDF2
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import os
import json
import shutil
import asyncio
import warnings
import streamlit as st
from tools import PodcastAudioGenerator, PodcastMixer, VoiceConfig

# Import authentication module
from auth import (
    init_database,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_password,
    verify_user_email,
    update_last_login,
    create_verification_token,
    get_verification_token,
    consume_verification_token,
    create_reset_token,
    get_reset_token,
    consume_reset_token,
    EmailService,
    SecurityManager,
    generate_verification_link,
    generate_reset_link,
    sanitize_email
)

# Suppress the function_call warning - it's expected behavior when agents use tools
warnings.filterwarnings('ignore', message='.*non-text parts in the response.*')
warnings.filterwarnings('ignore', message='.*function_call.*')
warnings.filterwarnings('ignore', message='.*App name mismatch.*')
warnings.filterwarnings('ignore', message='.*app name.*')


# Load environment variables (but don't use GOOGLE_API_KEY from .env - user must provide it in UI)
load_dotenv()

# Set default for Vertex AI (user will provide API key via UI)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"


def setup_directories():
    """Set up organized directory structure."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    dirs = {
        'BASE': f'outputs/{timestamp}',
        'SEGMENTS': f'outputs/{timestamp}/segments',
        'FINAL': f'outputs/{timestamp}/podcast',
        'DATA': f'outputs/{timestamp}/data'
    }
    
    for directory in dirs.values():
        os.makedirs(directory, exist_ok=True)
    
    return dirs


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text content
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        raise ValueError(f"Error reading PDF: {str(e)}")
    
    return text


# --- Pydantic Models ---
class PaperSummary(BaseModel):
    """Summary of a research paper."""
    title: str = Field(..., description="Title of the research paper")
    main_findings: List[str] = Field(..., description="Key findings as a list of strings")
    methodology: str = Field(..., description="Research methodology as a single text block")
    key_implications: List[str] = Field(..., description="Implications as a list of strings")
    limitations: List[str] = Field(..., description="Limitations as a list of strings")
    future_work: List[str] = Field(..., description="Future research directions as a list")
    summary_date: str = Field(..., description="Timestamp of summary creation")


class DialogueLine(BaseModel):
    """Dialogue line for a podcast script."""
    speaker: str = Field(..., description="Name of the speaker (Sarah or Dennis)")
    text: str = Field(..., description="The actual dialogue line")


class PodcastScript(BaseModel):
    """Podcast script with dialogue lines."""
    dialogue: List[DialogueLine] = Field(..., description="Ordered list of dialogue lines")


# Global variables for audio generation context
_audio_context = {}


def generate_audio_segments(enhanced_script: str) -> Dict[str, Any]:
    """
    Generate audio segments from podcast script.
    This function is called by the AudioGenerator agent via FunctionTool.
    
    Args:
        enhanced_script: The enhanced podcast script (JSON string or text containing JSON)
        
    Returns:
        Dictionary with status, final_podcast path, and segment files
    """
    global _audio_context
    try:
        # Parse script - handle both JSON string and text
        script_data = None
        if isinstance(enhanced_script, str):
            # Try to extract JSON if wrapped in text
            if enhanced_script.strip().startswith('{'):
                script_data = json.loads(enhanced_script)
            else:
                # Try to find JSON in text
                import re
                json_match = re.search(r'\{.*\}', enhanced_script, re.DOTALL)
                if json_match:
                    script_data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not find valid JSON in script")
        else:
            script_data = enhanced_script
        
        if not script_data or 'dialogue' not in script_data:
            raise ValueError("Invalid script format: missing 'dialogue' key")
        
        segments_dir = _audio_context.get('segments_dir', 'outputs/segments')
        final_dir = _audio_context.get('final_dir', 'outputs/podcast')
        
        # Initialize audio generator
        audio_generator = PodcastAudioGenerator(output_dir=segments_dir)
        
        # Add voices using Google TTS prebuilt voices
        # Available voices: Kore, Puck, Charon, Fenrir, Kore (male), Puck (female), etc.
        # Sarah uses a female voice, Dennis uses a male voice
        sarah_voice = os.getenv("SARAH_VOICE_NAME", "Kore")  # Default to Kore (female)
        dennis_voice = os.getenv("DENNIS_VOICE_NAME", "Puck")  # Default to Puck (male)
        
        audio_generator.add_voice(
            "Dennis", 
            dennis_voice
        )
        
        audio_generator.add_voice(
            "Sarah", 
            sarah_voice
        )
        
        # Convert dialogue to list of dicts
        dialogue_list = []
        for line in script_data.get('dialogue', []):
            if isinstance(line, dict):
                speaker = line.get('speaker', '').strip()
                text = line.get('text', '').strip()
                if speaker and text:
                    dialogue_list.append({
                        'speaker': speaker,
                        'text': text
                    })
        
        if not dialogue_list:
            raise ValueError("No valid dialogue found in script")
        
        # Generate audio segments
        audio_files = audio_generator.generate_audio(dialogue_list)
        
        if not audio_files:
            raise ValueError("No audio files were generated")
        
        # Mix audio
        podcast_mixer = PodcastMixer(output_dir=final_dir)
        final_podcast_path = podcast_mixer.mix_audio(audio_files)
        
        return {
            "status": "success",
            "final_podcast": final_podcast_path,
            "segment_files": audio_files,
            "message": f"Audio generation successful! Generated {len(audio_files)} segments. Final podcast saved to: {final_podcast_path}"
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "error": error_msg,
            "message": f"Error generating audio: {error_msg}"
        }


def generate_podcast(pdf_file_path: str, progress_callback=None) -> Optional[str]:
    """
    Generate a podcast from a research paper PDF using Google ADK multi-agent system.
    
    Args:
        pdf_file_path: Path to the PDF file
        progress_callback: Optional function to call with progress updates
        
    Returns:
        Path to the generated podcast audio file, or None if generation failed
    """
    try:
        # Setup directories
        if progress_callback:
            progress_callback("Setting up directories...")
        dirs = setup_directories()
        
        # Extract text from PDF
        if progress_callback:
            progress_callback("Extracting text from PDF...")
        paper_text = extract_text_from_pdf(pdf_file_path)
        
        # Limit text length for API
        paper_text_limited = paper_text[:50000] if len(paper_text) > 50000 else paper_text
        
        # Initialize audio context
        global _audio_context
        _audio_context = {
            'segments_dir': dirs['SEGMENTS'],
            'final_dir': dirs['FINAL'],
            'data_dir': dirs['DATA']
        }
        
        # Create audio generation tool
        audio_tool = FunctionTool(generate_audio_segments)
        
        # Step 1: Research Analyst Agent
        if progress_callback:
            progress_callback("Initializing research analyst agent...")
        research_analyst = Agent(
            name="ResearchAnalyst",
            model="gemini-2.0-flash-exp",
            instruction="""You're a PhD researcher with a talent for breaking down complex
            academic papers into clear, understandable summaries. You excel at identifying
            key findings and their real-world implications. 
            
            Analyze the provided research paper text and create a comprehensive summary that includes:
            1. Main findings and conclusions
            2. Methodology overview
            3. Key implications for the field
            4. Limitations of the study
            5. Suggested future research directions
            
            Make the summary accessible to an educated general audience while maintaining accuracy.
            Return your analysis as a structured JSON with the following fields:
            - title: Title of the research paper
            - main_findings: List of key findings
            - methodology: Research methodology description
            - key_implications: List of implications
            - limitations: List of limitations
            - future_work: List of future research directions
            - summary_date: Current date in ISO format (use: {datetime.now().isoformat()})
            
            Format your response as valid JSON only, no additional text.""",
            output_key="paper_summary"
        )
        
        # Step 2: Research Support Agent
        if progress_callback:
            progress_callback("Initializing research support agent...")
        research_support = Agent(
            name="ResearchSupport",
            model="gemini-2.0-flash-exp",
            instruction="""You're a versatile research assistant who excels at finding 
            supplementary information across academic fields. You have a talent for 
            connecting academic research with real-world applications, current events, 
            and practical examples, regardless of the field.
            
            Based on this research paper summary: {paper_summary}
            
            Find recent and relevant supporting materials that add context and real-world 
            perspective to the topic. Focus on:
            1. Recent developments in the field (within last 2 years)
            2. Practical applications and case studies
            3. Industry reports and expert opinions
            4. Different perspectives and alternative approaches
            5. Real-world impact and adoption
            
            Provide a structured collection of relevant supporting materials, examples, 
            and context that would enhance understanding of the research topic.
            Format your response as a clear, organized text with sections.""",
            output_key="supporting_research"
        )
        
        # Step 3: Script Writer Agent
        if progress_callback:
            progress_callback("Initializing script writer agent...")
        script_writer = Agent(
            name="ScriptWriter",
            model="gemini-2.0-flash-exp",
            instruction="""You're a skilled podcast writer who specializes in making technical 
            content engaging and accessible. You create natural dialogue between two hosts: 
            Dennis (a knowledgeable expert who explains concepts clearly) and Sarah (an informed 
            co-host who asks thoughtful questions and helps guide the discussion).
            
            Using this paper summary: {paper_summary}
            And this supporting research: {supporting_research}
            
            Create an engaging and informative podcast conversation between Dennis and Sarah. 
            Make it feel natural while clearly distinguishing between paper findings and 
            supplementary research.
            
            Source Attribution Guidelines:
            • For Paper Content: "According to the paper...", "The researchers found that...", etc.
            • For Supporting Research: "I recently read about...", "There's some interesting related work...", etc.
            
            Host Dynamics:
            - Dennis: A knowledgeable but relatable expert who explains technical concepts with enthusiasm
            - Sarah: An engaged and curious co-host who asks insightful questions
            
            Return the script as a JSON object with a 'dialogue' array, where each item has:
            - speaker: Either "Dennis" or "Sarah"
            - text: The dialogue line
            
            Format your response as valid JSON only, with this exact structure:
            {{"dialogue": [{{"speaker": "Dennis", "text": "..."}}, {{"speaker": "Sarah", "text": "..."}}]}}""",
            output_key="podcast_script"
        )
        
        # Step 4: Script Enhancer Agent
        if progress_callback:
            progress_callback("Initializing script enhancer agent...")
        script_enhancer = Agent(
            name="ScriptEnhancer",
            model="gemini-2.0-flash-exp",
            instruction="""You're a veteran podcast producer who specializes in making technical 
            content both entertaining and informative. You excel at adding natural humor, 
            relatable analogies, and engaging banter while ensuring the core technical content 
            remains accurate and valuable.
            
            IMPORTANT RULES:
            1. NEVER change the host names - always keep Dennis and Sarah exactly as they are
            2. NEVER add explicit reaction markers like *chuckles*, *laughs*, etc.
            3. NEVER add new hosts or characters
            
            Enhance this podcast script: {podcast_script}
            
            Enhancement Guidelines:
            1. Add natural verbal reactions ("Oh that's fascinating", "Wow", etc.)
            2. Improve flow with smooth transitions
            3. Maintain technical accuracy
            4. Add engagement through analogies and examples
            5. Express enthusiasm through natural dialogue
            
            Return the enhanced script as a JSON object with the same structure:
            {{"dialogue": [{{"speaker": "Dennis", "text": "..."}}, {{"speaker": "Sarah", "text": "..."}}]}}
            
            Format your response as valid JSON only.""",
            output_key="enhanced_script"
        )
        
        # Step 5: Audio Generator Agent
        if progress_callback:
            progress_callback("Initializing audio generator agent...")
        audio_generator_agent = Agent(
            name="AudioGenerator",
            model="gemini-2.0-flash-exp",
            instruction="""You are responsible for generating the final podcast audio.
            
            You have access to the enhanced podcast script from the previous step: {enhanced_script}
            
            IMPORTANT: You MUST call the generate_audio_segments function with the enhanced_script as the argument.
            The function requires the enhanced script (which is a JSON string or text containing JSON).
            
            Steps:
            1. Take the enhanced_script from the context above
            2. Call generate_audio_segments(enhanced_script) with the script as the argument
            3. Report the result from the function call
            
            The function will return a dictionary with status, final_podcast path, and other details.
            Report the final_podcast path if the status is "success", or report the error if status is "error".""",
            tools=[audio_tool],
            output_key="audio_result"
        )
        
        # Create Sequential Agent workflow
        if progress_callback:
            progress_callback("Creating multi-agent workflow...")
        root_agent = SequentialAgent(
            name="PodcastGenerationPipeline",
            sub_agents=[
                research_analyst,
                research_support,
                script_writer,
                script_enhancer,
                audio_generator_agent
            ]
        )
        
        # Run the workflow
        if progress_callback:
            progress_callback("Starting podcast generation process...")
        runner = InMemoryRunner(agent=root_agent)
        
        # Create the initial prompt with paper text
        initial_prompt = f"""Analyze this research paper and create a podcast:{paper_text_limited} Begin the analysis process."""
        
        # Execute the workflow (handle async)
        # Use run_debug to properly handle function calls and get full response
        # Suppress app name mismatch warnings during execution
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*App name mismatch.*')
            warnings.filterwarnings('ignore', message='.*app name.*')
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # run_debug properly handles function calls and returns full response
                response = loop.run_until_complete(runner.run_debug(initial_prompt))
                loop.close()
            except Exception as e:
                # If async fails, try to get more details about the error
                error_msg = str(e)
                if progress_callback:
                    progress_callback(f"Error during workflow execution: {error_msg}")
                raise RuntimeError(f"Failed to execute workflow: {error_msg}")
        
        # Save intermediate results
        if progress_callback:
            progress_callback("Saving intermediate results...")
        
        # Try to extract results from the response
        # The response structure may vary - try different access patterns
        state = {}
        if hasattr(response, 'state'):
            state = response.state
        elif hasattr(response, 'get'):
            state = response
        elif isinstance(response, dict):
            state = response
        
        # Save paper summary if available
        if 'paper_summary' in state:
            summary_path = os.path.join(dirs['DATA'], "paper_summary.json")
            try:
                summary_text = state.get('paper_summary', '') if isinstance(state, dict) else getattr(state, 'paper_summary', '')
                # Try to parse as JSON
                if summary_text.strip().startswith('{'):
                    summary_json = json.loads(summary_text)
                else:
                    # Extract JSON from text if wrapped
                    import re
                    json_match = re.search(r'\{.*\}', summary_text, re.DOTALL)
                    if json_match:
                        summary_json = json.loads(json_match.group())
                    else:
                        summary_json = {"summary": summary_text}
                with open(summary_path, 'w') as f:
                    json.dump(summary_json, f, indent=2)
            except Exception as e:
                print(f"Error saving summary: {e}")
        
        # Save supporting research
        if 'supporting_research' in state:
            support_path = os.path.join(dirs['DATA'], "supporting_research.json")
            support_text = state.get('supporting_research', '') if isinstance(state, dict) else getattr(state, 'supporting_research', '')
            with open(support_path, 'w') as f:
                json.dump({"research": support_text}, f, indent=2)
        
        # Save scripts
        if 'podcast_script' in state:
            script_path = os.path.join(dirs['DATA'], "podcast_script.json")
            try:
                script_text = state.get('podcast_script', '') if isinstance(state, dict) else getattr(state, 'podcast_script', '')
                if script_text.strip().startswith('{'):
                    script_json = json.loads(script_text)
                else:
                    import re
                    json_match = re.search(r'\{.*\}', script_text, re.DOTALL)
                    if json_match:
                        script_json = json.loads(json_match.group())
                    else:
                        script_json = {"dialogue": []}
                with open(script_path, 'w') as f:
                    json.dump(script_json, f, indent=2)
            except Exception as e:
                print(f"Error saving script: {e}")
        
        if 'enhanced_script' in state:
            enhanced_script_path = os.path.join(dirs['DATA'], "enhanced_podcast_script.json")
            try:
                enhanced_text = state.get('enhanced_script', '') if isinstance(state, dict) else getattr(state, 'enhanced_script', '')
                if enhanced_text.strip().startswith('{'):
                    enhanced_json = json.loads(enhanced_text)
                else:
                    import re
                    json_match = re.search(r'\{.*\}', enhanced_text, re.DOTALL)
                    if json_match:
                        enhanced_json = json.loads(json_match.group())
                    else:
                        enhanced_json = {"dialogue": []}
                with open(enhanced_script_path, 'w') as f:
                    json.dump(enhanced_json, f, indent=2)
            except Exception as e:
                print(f"Error saving enhanced script: {e}")
        
        # Extract final podcast path from audio result
        if progress_callback:
            progress_callback("Extracting podcast file path...")
        
        # Check if audio was generated via FunctionTool
        final_podcast_path = None
        
        if 'audio_result' in state:
            audio_result = state.get('audio_result', '') if isinstance(state, dict) else getattr(state, 'audio_result', '')
            
            # Try to extract from the result
            try:
                # If it's a string, try to parse it or extract JSON
                if isinstance(audio_result, str):
                    # Check if it contains JSON
                    import re
                    json_match = re.search(r'\{.*\}', audio_result, re.DOTALL)
                    if json_match:
                        audio_result_dict = json.loads(json_match.group())
                        if isinstance(audio_result_dict, dict) and 'final_podcast' in audio_result_dict:
                            final_podcast_path = audio_result_dict['final_podcast']
                    # Check if it mentions a path
                    elif 'saved to:' in audio_result or 'Final podcast' in audio_result:
                        path_match = re.search(r'(?:saved to:|Final podcast)[:\s]+(.+?)(?:\n|$)', audio_result)
                        if path_match:
                            final_podcast_path = path_match.group(1).strip()
                
                # If it's already a dict
                elif isinstance(audio_result, dict):
                    if 'final_podcast' in audio_result:
                        final_podcast_path = audio_result['final_podcast']
                    elif 'status' in audio_result and audio_result.get('status') == 'success':
                        final_podcast_path = audio_result.get('final_podcast')
                
                # Verify the path exists
                if final_podcast_path and os.path.exists(final_podcast_path):
                    if progress_callback:
                        progress_callback("Podcast generation complete!")
                    return final_podcast_path
                    
            except Exception as e:
                print(f"Error parsing audio result: {e}")
                print(f"Audio result type: {type(audio_result)}")
                print(f"Audio result preview: {str(audio_result)[:500]}")
        
        # Fallback: Check expected path
        expected_path = os.path.join(dirs['FINAL'], "podcast_final.mp3")
        if os.path.exists(expected_path):
            if progress_callback:
                progress_callback("Podcast generation complete!")
            return expected_path
        
        # If audio wasn't generated, try to generate it directly as fallback
        if progress_callback:
            progress_callback("Audio generation via agent may have failed. Attempting direct generation...")
        
        # Get enhanced script from state for fallback
        enhanced_script_text = ""
        if 'enhanced_script' in state:
            enhanced_script_text = state.get('enhanced_script', '') if isinstance(state, dict) else getattr(state, 'enhanced_script', '')
        
        if not enhanced_script_text:
            # Try to get from saved file
            enhanced_script_path = os.path.join(dirs['DATA'], "enhanced_podcast_script.json")
            if os.path.exists(enhanced_script_path):
                with open(enhanced_script_path, 'r') as f:
                    enhanced_script_data = json.load(f)
                    enhanced_script_text = json.dumps(enhanced_script_data)
        
        if enhanced_script_text:
            # Call the function directly as fallback
            try:
                audio_result = generate_audio_segments(enhanced_script_text)
                if isinstance(audio_result, dict) and audio_result.get('status') == 'success':
                    final_path = audio_result.get('final_podcast')
                    if final_path and os.path.exists(final_path):
                        if progress_callback:
                            progress_callback("Podcast generation complete (via fallback)!")
                        return final_path
                    elif final_path:
                        # Path was returned but file doesn't exist - check expected location
                        expected_path = os.path.join(dirs['FINAL'], "podcast_final.mp3")
                        if os.path.exists(expected_path):
                            return expected_path
            except Exception as e:
                error_msg = f"Fallback audio generation also failed: {str(e)}"
                if progress_callback:
                    progress_callback(error_msg)
                # Save error for debugging
                error_path = os.path.join(dirs['DATA'], "audio_generation_error.json")
                with open(error_path, 'w') as f:
                    json.dump({
                        "error": str(e),
                        "audio_result_from_agent": str(audio_result)[:500] if 'audio_result' in locals() else None,
                        "enhanced_script_preview": enhanced_script_text[:500] if enhanced_script_text else None
                    }, f, indent=2)
        
        # If we get here, audio generation failed
        raise ValueError("Failed to generate podcast audio. Check audio_generation_error.json for details.")
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error: {str(e)}")
        raise


# ============================================================================
# AUTHENTICATION UI FUNCTIONS
# ============================================================================

def init_auth_session_state():
    """Initialize authentication-related session state."""
    if 'auth_state' not in st.session_state:
        st.session_state.auth_state = None  # None, 'awaiting_verification', 'awaiting_password', 'authenticated'
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'auth_page' not in st.session_state:
        st.session_state.auth_page = 'login'  # 'login', 'signup', 'forgot_password', 'create_password', 'reset_password'
    if 'pending_user_id' not in st.session_state:
        st.session_state.pending_user_id = None


def is_authenticated() -> bool:
    """Check if user is fully authenticated."""
    return (
        st.session_state.get('auth_state') == 'authenticated' and
        st.session_state.get('user') is not None
    )


def logout():
    """Clear session and logout user."""
    st.session_state.auth_state = None
    st.session_state.user = None
    st.session_state.auth_page = 'login'
    st.session_state.pending_user_id = None
    st.rerun()


def handle_email_verification():
    """Process email verification from URL."""
    query_params = st.query_params

    if 'verify' in query_params:
        token = query_params.get('verify')
        token_data = get_verification_token(token)

        if token_data:
            # Valid token - verify email
            verify_user_email(token_data.user_id)
            consume_verification_token(token)

            st.session_state.auth_page = 'create_password'
            st.session_state.pending_user_id = token_data.user_id
            st.session_state.auth_state = 'awaiting_password'
            st.query_params.clear()
            st.success("Email verified successfully! Please create your password.")
        else:
            st.error("Invalid or expired verification link. Please request a new one.")
            st.query_params.clear()


def handle_password_reset_link():
    """Process password reset from URL."""
    query_params = st.query_params

    if 'reset' in query_params:
        token = query_params.get('reset')
        token_data = get_reset_token(token)

        if token_data:
            st.session_state.auth_page = 'reset_password'
            st.session_state.pending_user_id = token_data.user_id
            st.session_state.reset_token = token
        else:
            st.error("Invalid or expired reset link. Please request a new one.")
            st.query_params.clear()


def show_login_page():
    """Display login form."""
    st.header("Sign In")

    # Email/password login
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if email and password:
                user = get_user_by_email(sanitize_email(email))

                if user and user.password_hash:
                    if SecurityManager.verify_password(password, user.password_hash):
                        if user.is_email_verified:
                            st.session_state.auth_state = 'authenticated'
                            st.session_state.user = {
                                'id': user.id,
                                'email': user.email
                            }
                            update_last_login(user.id)
                            st.rerun()
                        else:
                            st.error("Please verify your email first. Check your inbox.")
                    else:
                        st.error("Invalid email or password.")
                else:
                    st.error("Invalid email or password.")
            else:
                st.error("Please enter both email and password.")

    # Navigation links
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Forgot Password?", use_container_width=True):
            st.session_state.auth_page = 'forgot_password'
            st.rerun()
    with col2:
        if st.button("Create Account", use_container_width=True):
            st.session_state.auth_page = 'signup'
            st.rerun()


def show_signup_page():
    """Display email-based signup form."""
    st.header("Create Account")

    st.info("Enter your email to create an account. We'll send you a verification link.")

    with st.form("signup_form"):
        email = st.text_input("Email Address")
        submitted = st.form_submit_button("Sign Up", use_container_width=True)

        if submitted:
            if email:
                email = sanitize_email(email)

                # Check if user already exists
                existing_user = get_user_by_email(email)

                if existing_user:
                    if existing_user.is_email_verified and existing_user.password_hash:
                        st.error("An account with this email already exists. Please sign in.")
                    elif existing_user.is_email_verified:
                        # Email verified but no password - go to password creation
                        st.session_state.auth_page = 'create_password'
                        st.session_state.pending_user_id = existing_user.id
                        st.rerun()
                    else:
                        # Resend verification email
                        token = SecurityManager.generate_token()
                        expires_at = SecurityManager.get_verification_token_expiry()
                        create_verification_token(existing_user.id, token, expires_at)

                        email_service = EmailService()
                        verification_link = generate_verification_link(token)
                        email_service.send_verification_email(email, verification_link)

                        st.session_state.auth_state = 'awaiting_verification'
                        st.session_state.pending_user_id = existing_user.id
                        st.rerun()
                else:
                    # Create new user
                    new_user = create_user(email)

                    if new_user:
                        # Generate verification token
                        token = SecurityManager.generate_token()
                        expires_at = SecurityManager.get_verification_token_expiry()
                        create_verification_token(new_user.id, token, expires_at)

                        # Send verification email
                        email_service = EmailService()
                        verification_link = generate_verification_link(token)
                        email_service.send_verification_email(email, verification_link)

                        # Send admin notification
                        email_service.send_admin_notification(email)

                        st.session_state.auth_state = 'awaiting_verification'
                        st.session_state.pending_user_id = new_user.id
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")
            else:
                st.error("Please enter your email address.")

    if st.button("Back to Sign In"):
        st.session_state.auth_page = 'login'
        st.rerun()


def show_forgot_password_page():
    """Display forgot password form."""
    st.header("Reset Password")

    with st.form("forgot_password_form"):
        email = st.text_input("Enter your email address")
        submitted = st.form_submit_button("Send Reset Link", use_container_width=True)

        if submitted:
            if email:
                user = get_user_by_email(sanitize_email(email))

                # Always show success to prevent email enumeration
                st.success("If an account exists with this email, a password reset link has been sent.")

                if user:
                    token = SecurityManager.generate_token()
                    expires_at = SecurityManager.get_reset_token_expiry()
                    create_reset_token(user.id, token, expires_at)

                    email_service = EmailService()
                    reset_link = generate_reset_link(token)
                    email_service.send_password_reset_email(email, reset_link)
            else:
                st.error("Please enter your email address.")

    if st.button("Back to Sign In"):
        st.session_state.auth_page = 'login'
        st.rerun()


def show_create_password_page():
    """Display password creation form after email verification."""
    st.header("Create Your Password")

    user_id = st.session_state.get('pending_user_id')
    if not user_id:
        st.error("Session expired. Please sign up again.")
        st.session_state.auth_page = 'signup'
        st.rerun()
        return

    user = get_user_by_id(user_id)
    if not user:
        st.error("User not found. Please sign up again.")
        st.session_state.auth_page = 'signup'
        st.rerun()
        return

    st.info(f"Creating password for: {user.email}")

    st.markdown("""
    **Password requirements:**
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """)

    with st.form("create_password_form"):
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Password", use_container_width=True)

        if submitted:
            if password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    is_valid, message = SecurityManager.validate_password_strength(password)
                    if not is_valid:
                        st.error(message)
                    else:
                        password_hash = SecurityManager.hash_password(password)
                        update_user_password(user_id, password_hash)

                        st.session_state.auth_state = 'authenticated'
                        st.session_state.user = {
                            'id': user.id,
                            'email': user.email
                        }
                        st.session_state.pending_user_id = None
                        update_last_login(user.id)
                        st.success("Password created successfully!")
                        st.rerun()
            else:
                st.error("Please enter and confirm your password.")


def show_reset_password_page():
    """Display password reset form."""
    st.header("Reset Your Password")

    user_id = st.session_state.get('pending_user_id')
    reset_token = st.session_state.get('reset_token')

    if not user_id or not reset_token:
        st.error("Invalid reset session. Please request a new password reset.")
        st.session_state.auth_page = 'login'
        st.rerun()
        return

    st.markdown("""
    **Password requirements:**
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """)

    with st.form("reset_password_form"):
        password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Reset Password", use_container_width=True)

        if submitted:
            if password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    is_valid, message = SecurityManager.validate_password_strength(password)
                    if not is_valid:
                        st.error(message)
                    else:
                        password_hash = SecurityManager.hash_password(password)
                        update_user_password(user_id, password_hash)
                        consume_reset_token(reset_token)

                        st.session_state.pending_user_id = None
                        st.session_state.reset_token = None
                        st.session_state.auth_page = 'login'
                        st.query_params.clear()
                        st.success("Password reset successfully! Please sign in.")
                        st.rerun()
            else:
                st.error("Please enter and confirm your new password.")


def show_awaiting_verification_page():
    """Display message when awaiting email verification."""
    st.header("Verify Your Email")

    user_id = st.session_state.get('pending_user_id')
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            st.info(f"A verification email has been sent to **{user.email}**")

    st.markdown("""
    Please check your inbox and click the verification link to continue.

    **Didn't receive the email?**
    - Check your spam folder
    - Make sure you entered the correct email address
    """)

    if st.button("Resend Verification Email"):
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                token = SecurityManager.generate_token()
                expires_at = SecurityManager.get_verification_token_expiry()
                create_verification_token(user.id, token, expires_at)

                email_service = EmailService()
                verification_link = generate_verification_link(token)
                email_service.send_verification_email(user.email, verification_link)
                st.success("Verification email sent!")

    if st.button("Back to Sign In"):
        st.session_state.auth_state = None
        st.session_state.auth_page = 'login'
        st.session_state.pending_user_id = None
        st.rerun()


def show_auth_ui():
    """Display authentication interface."""
    st.title("AI Podcast Generator")
    st.markdown("Convert research papers into engaging podcast conversations.")

    # Check if awaiting verification
    if st.session_state.get('auth_state') == 'awaiting_verification':
        show_awaiting_verification_page()
        return

    auth_page = st.session_state.get('auth_page', 'login')

    if auth_page == 'login':
        show_login_page()
    elif auth_page == 'signup':
        show_signup_page()
    elif auth_page == 'forgot_password':
        show_forgot_password_page()
    elif auth_page == 'create_password':
        show_create_password_page()
    elif auth_page == 'reset_password':
        show_reset_password_page()


# ============================================================================
# STREAMLIT UI
# ============================================================================

# Streamlit UI
def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="AI Agents Podcast Generator",
        page_icon="🎙️",
        layout="wide"
    )

    # Initialize database
    init_database()

    # Initialize authentication session state
    init_auth_session_state()

    # Initialize app session state
    if 'podcast_path' not in st.session_state:
        st.session_state.podcast_path = None
    if 'status' not in st.session_state:
        st.session_state.status = None
    if 'google_api_key' not in st.session_state:
        st.session_state.google_api_key = None

    # Handle URL query parameters for authentication
    query_params = st.query_params

    # Handle email verification
    if 'verify' in query_params:
        handle_email_verification()

    # Handle password reset
    if 'reset' in query_params:
        handle_password_reset_link()

    # Check authentication - show auth UI if not authenticated
    if not is_authenticated():
        show_auth_ui()
        st.stop()

    # User is authenticated - show main app
    st.title("🎙️ AI Agents Podcast Generator")
    st.markdown("Convert research papers into engaging podcast conversations using Google ADK multi-agent system.")

    # API Key Input Section (at the top, before everything else)
    st.sidebar.header("👤 Account")
    user = st.session_state.get('user', {})
    st.sidebar.markdown(f"**{user.get('email', 'Unknown')}**")
    if st.sidebar.button("Logout", use_container_width=True):
        logout()
    st.sidebar.divider()

    st.sidebar.header("🔑 API Configuration")
    st.sidebar.markdown("**Required**: Enter your Google API Key to use the application.")
    
    # Get API key from session state if it exists, otherwise empty
    default_key = st.session_state.google_api_key if st.session_state.google_api_key else ""
    
    # API Key input - always required, never pre-filled from .env
    api_key = st.sidebar.text_input(
        "Google API Key *",
        value=default_key,
        type="password",
        help="Enter your Google API Key for Gemini models and TTS. Get it from https://makersuite.google.com/app/apikey",
        key="api_key_input",
        placeholder="Enter your Google API Key here"
    )
    
    # Validate API key - REQUIRED FIELD
    if not api_key or not api_key.strip():
        st.error("❌ **Error: Google API Key is required!**")
        st.markdown("""
        ### ⚠️ Application cannot proceed without API Key
        
        **Please provide your Google API Key:**
        
        1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Enter it in the sidebar above
        3. The application will not work without a valid API key
        
        **Note**: 
        - Your API key is stored only in your browser session and is not saved to disk
        - The application does NOT use API keys from .env file - you must enter it here
        - The key is required for all operations (Gemini models and Google TTS)
        """)
        st.stop()
    
    # Store API key in session state and set as environment variable
    # This overwrites any existing GOOGLE_API_KEY from .env
    st.session_state.google_api_key = api_key.strip()
    os.environ["GOOGLE_API_KEY"] = st.session_state.google_api_key
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
    
    # Show confirmation
    if api_key.strip():
        st.sidebar.success("✅ API Key configured")
    
    # Sidebar for file upload
    with st.sidebar:
        st.header("📄 Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload a research paper PDF to convert into a podcast"
        )
        
        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")
            
            # Create uploads directory for temporary storage
            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save uploaded file temporarily
            pdf_path = os.path.join(upload_dir, uploaded_file.name)
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Generate button
            if st.button("Generate Podcast", type="primary", use_container_width=True):
                # Verify API key is still set
                if not st.session_state.google_api_key or not os.getenv("GOOGLE_API_KEY"):
                    st.error("❌ Google API Key is required! Please enter it in the sidebar.")
                    st.stop()
                else:
                    st.session_state.status = "Generating podcast..."
                    st.session_state.podcast_path = None
                    
                    # Create a placeholder for status updates
                    status_placeholder = st.empty()
                    progress_bar = st.progress(0)
                    
                    try:
                        # Generate podcast with progress callback
                        def progress_callback(message):
                            status_placeholder.text(f"Status: {message}")
                        
                        podcast_path = generate_podcast(pdf_path, progress_callback=progress_callback)
                        
                        if podcast_path and os.path.exists(podcast_path):
                            st.session_state.podcast_path = podcast_path
                            st.session_state.status = "Podcast generated successfully!"
                            progress_bar.progress(100)
                            st.success("Podcast generated successfully!")
                        else:
                            st.error("Failed to generate podcast. Please check the logs for details.")
                            st.session_state.status = "Failed to generate podcast"
                    except Exception as e:
                        st.error(f"Error generating podcast: {str(e)}")
                        st.session_state.status = f"Error: {str(e)}"
                    finally:
                        progress_bar.empty()
                        status_placeholder.empty()
    
    # Main content area
    if st.session_state.podcast_path and os.path.exists(st.session_state.podcast_path):
        st.header("🎧 Your Podcast")
        st.success("Podcast generated successfully! Listen to it below.")
        
        # Display audio player
        with open(st.session_state.podcast_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mp3", autoplay=False)
        
        # Download button
        st.download_button(
            label="Download Podcast",
            data=audio_bytes,
            file_name=f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3",
            mime="audio/mp3",
            use_container_width=True
        )
    elif st.session_state.status and "Error" in st.session_state.status:
        st.error(st.session_state.status)
    else:
        # Instructions
        if st.session_state.google_api_key:
            st.info("👆 Upload a PDF file in the sidebar to get started!")
        else:
            st.warning("⚠️ Please enter your Google API Key in the sidebar to continue.")
        
        st.markdown("""
        ### How it works:
        1. **Enter API Key**: Provide your Google API Key in the sidebar (required)
        2. **Upload a PDF**: Select a research paper PDF file
        3. **Generate**: Click the "Generate Podcast" button
        4. **Listen**: Once generated, listen to your podcast using the audio player
        
        ### Features:
        - 🤖 Multi-agent system using Google ADK
        - 📝 Natural dialogue generation between two hosts
        - 🎙️ High-quality voice synthesis using Google TTS
        - 🎵 Professional audio mixing
        
        ### Getting Your API Key:
        Get your Google API Key from [Google AI Studio](https://makersuite.google.com/app/apikey)
        """)


if __name__ == "__main__":
    import sys
    
    # Check if running from command line (non-streamlit) for backward compatibility
    if len(sys.argv) > 1 and sys.argv[1] != "run":
        # Original command-line mode (for backward compatibility)
        pdf_path = sys.argv[1] if len(sys.argv) > 1 else "AgentQuality.pdf"
        print(f"Generating podcast from {pdf_path}...")
        
        def print_progress(message):
            print(f"Progress: {message}")
        
        result = generate_podcast(pdf_path, progress_callback=print_progress)
        if result:
            print(f"Podcast generated successfully: {result}")
        else:
            print("Failed to generate podcast")
    else:
        # Streamlit mode
        main()
