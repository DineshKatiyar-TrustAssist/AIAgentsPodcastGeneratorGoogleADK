"""
AI Agents Podcast Generator using Google ADK.
Converts research papers into engaging podcast conversations.
"""
from google.generativeai import configure, GenerativeModel
import PyPDF2
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
import os
import json
import shutil
import streamlit as st
from tools import PodcastAudioGenerator, PodcastMixer, VoiceConfig


# Load environment variables
load_dotenv()

# Configure Google Generative AI
if os.getenv("GOOGLE_API_KEY"):
    configure(api_key=os.getenv("GOOGLE_API_KEY"))


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


class AudioGeneration(BaseModel):
    """Audio generation result with metadata."""
    segment_files: List[str] = Field(..., description="List of generated audio segment files")
    final_podcast: str = Field(..., description="Path to the final mixed podcast file")


# --- Agent Helper Functions ---
def get_research_analyst_model():
    """Get the research analyst model with instructions."""
    model = GenerativeModel(
        model_name='gemini-2.0-flash-exp',
        system_instruction="""You're a PhD researcher with a talent for breaking down complex
        academic papers into clear, understandable summaries. You excel at identifying
        key findings and their real-world implications. When analyzing a research paper,
        create a comprehensive summary that includes:
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
        - summary_date: Current date in ISO format"""
    )
    return model


def get_research_support_model():
    """Get the research support model with instructions."""
    model = GenerativeModel(
        model_name='gemini-2.0-flash-exp',
        system_instruction="""You're a versatile research assistant who excels at finding 
        supplementary information across academic fields. You have a talent for 
        connecting academic research with real-world applications, current events, 
        and practical examples, regardless of the field. You know how to find 
        credible sources and relevant discussions across various domains.
        
        After analyzing a paper summary, find recent and relevant supporting 
        materials that add context and real-world perspective to the topic.
        
        Focus on:
        1. Recent developments in the field (within last 2 years)
        2. Practical applications and case studies
        3. Industry reports and expert opinions
        4. Different perspectives and alternative approaches
        5. Real-world impact and adoption
        
        Based on your knowledge and the paper summary, provide a structured
        collection of relevant supporting materials, examples, and context
        that would enhance understanding of the research topic."""
    )
    return model


def get_script_writer_model():
    """Get the script writer model with instructions."""
    model = GenerativeModel(
        model_name='gemini-2.0-flash-exp',
        system_instruction="""You're a skilled podcast writer who specializes in making technical 
        content engaging and accessible. You create natural dialogue between two hosts: 
        Sarah (a knowledgeable expert who explains concepts clearly) and Dennis (an informed 
        co-host who asks thoughtful questions and helps guide the discussion).
        
        Using the paper summary and supporting research, create an engaging and informative 
        podcast conversation between Sarah and Dennis. Make it feel natural while clearly 
        distinguishing between paper findings and supplementary research.
        
        Source Attribution Guidelines:
        • For Paper Content: "According to the paper...", "The researchers found that...", etc.
        • For Supporting Research: "I recently read about...", "There's some interesting related work...", etc.
        
        Host Dynamics:
        - Sarah: A knowledgeable but relatable expert who explains technical concepts with enthusiasm
        - Dennis: An engaged and curious co-host who asks insightful questions
        
        Return the script as a JSON with a 'dialogue' array, where each item has:
        - speaker: Either "Sarah" or "Dennis"
        - text: The dialogue line"""
    )
    return model


def get_script_enhancer_model():
    """Get the script enhancer model with instructions."""
    model = GenerativeModel(
        model_name='gemini-2.0-flash-exp',
        system_instruction="""You're a veteran podcast producer who specializes in making technical 
        content both entertaining and informative. You excel at adding natural humor, 
        relatable analogies, and engaging banter while ensuring the core technical content 
        remains accurate and valuable.
        
        IMPORTANT RULES:
        1. NEVER change the host names - always keep Sarah and Dennis exactly as they are
        2. NEVER add explicit reaction markers like *chuckles*, *laughs*, etc.
        3. NEVER add new hosts or characters
        
        Enhancement Guidelines:
        1. Add natural verbal reactions ("Oh that's fascinating", "Wow", etc.)
        2. Improve flow with smooth transitions
        3. Maintain technical accuracy
        4. Add engagement through analogies and examples
        5. Express enthusiasm through natural dialogue
        
        Return the enhanced script as a JSON with a 'dialogue' array, where each item has:
        - speaker: Either "Sarah" or "Dennis"
        - text: The enhanced dialogue line"""
    )
    return model


def generate_podcast(pdf_file_path: str, progress_callback=None) -> Optional[str]:
    """
    Generate a podcast from a research paper PDF using Google ADK agents.
    
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
        
        # Initialize models
        if progress_callback:
            progress_callback("Initializing AI models...")
        research_model = get_research_analyst_model()
        support_model = get_research_support_model()
        script_model = get_script_writer_model()
        enhancer_model = get_script_enhancer_model()
        
        # Configure audio tools
        if progress_callback:
            progress_callback("Configuring audio tools...")
        audio_generator = PodcastAudioGenerator(output_dir=dirs['SEGMENTS'])
        
        # Sarah: Enthusiastic expert
        audio_generator.add_voice(
            "Sarah", 
            os.getenv("CLAUDIA_VOICE_ID"),
            VoiceConfig(
                stability=0.35,
                similarity_boost=0.75,
                style=0.65,
                use_speaker_boost=True
            )
        )
        
        # Dennis: Engaged and curious
        audio_generator.add_voice(
            "Dennis", 
            os.getenv("BEN_VOICE_ID"),
            VoiceConfig(
                stability=0.4,
                similarity_boost=0.75,
                style=0.6,
                use_speaker_boost=True
            )
        )
        
        podcast_mixer = PodcastMixer(output_dir=dirs['FINAL'])
        
        # Step 1: Research Analysis
        if progress_callback:
            progress_callback("Analyzing research paper...")
        summary_prompt = f"""Analyze the following research paper and create a comprehensive summary:

{paper_text[:50000]}  # Limit text length for API

Create a structured summary with all key components."""
        
        response = research_model.generate_content(summary_prompt)
        summary_response = response.text
        
        # Parse summary (try to extract JSON from response)
        try:
            # Try to find JSON in the response
            if "```json" in summary_response:
                json_start = summary_response.find("```json") + 7
                json_end = summary_response.find("```", json_start)
                summary_json = json.loads(summary_response[json_start:json_end].strip())
            elif "{" in summary_response:
                json_start = summary_response.find("{")
                json_end = summary_response.rfind("}") + 1
                summary_json = json.loads(summary_response[json_start:json_end])
            else:
                # Fallback: create summary from text
                summary_json = {
                    "title": "Research Paper",
                    "main_findings": [summary_response[:200]],
                    "methodology": summary_response[:500],
                    "key_implications": [summary_response[:200]],
                    "limitations": [],
                    "future_work": [],
                    "summary_date": datetime.now().isoformat()
                }
        except json.JSONDecodeError:
            # Fallback summary
            summary_json = {
                "title": "Research Paper",
                "main_findings": [summary_response[:200]],
                "methodology": summary_response[:500],
                "key_implications": [summary_response[:200]],
                "limitations": [],
                "future_work": [],
                "summary_date": datetime.now().isoformat()
            }
        
        # Save summary
        summary_path = os.path.join(dirs['DATA'], "paper_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary_json, f, indent=2)
        
        # Step 2: Supporting Research
        if progress_callback:
            progress_callback("Finding supporting materials...")
        support_prompt = f"""Based on this research paper summary, find recent and relevant supporting materials:

{json.dumps(summary_json, indent=2)}

Find information that adds context, real-world applications, and different perspectives."""
        
        response = support_model.generate_content(support_prompt)
        supporting_research = response.text
        
        # Save supporting research
        support_path = os.path.join(dirs['DATA'], "supporting_research.json")
        with open(support_path, 'w') as f:
            json.dump({"research": supporting_research}, f, indent=2)
        
        # Step 3: Create Podcast Script
        if progress_callback:
            progress_callback("Creating podcast script...")
        script_prompt = f"""Create an engaging podcast script based on:

Paper Summary:
{json.dumps(summary_json, indent=2)}

Supporting Research:
{supporting_research}

Create a natural conversation between Sarah and Dennis that clearly distinguishes between paper findings and supplementary research."""
        
        response = script_model.generate_content(script_prompt)
        script_response = response.text
        
        # Parse script
        try:
            if "```json" in script_response:
                json_start = script_response.find("```json") + 7
                json_end = script_response.find("```", json_start)
                script_json = json.loads(script_response[json_start:json_end].strip())
            elif "{" in script_response:
                json_start = script_response.find("{")
                json_end = script_response.rfind("}") + 1
                script_json = json.loads(script_response[json_start:json_end])
            else:
                raise ValueError("No JSON found in script response")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse script JSON: {str(e)}")
        
        # Save initial script
        script_path = os.path.join(dirs['DATA'], "podcast_script.json")
        with open(script_path, 'w') as f:
            json.dump(script_json, f, indent=2)
        
        # Step 4: Enhance Script
        if progress_callback:
            progress_callback("Enhancing podcast script...")
        enhance_prompt = f"""Enhance this podcast script to be more engaging while maintaining accuracy:

{json.dumps(script_json, indent=2)}

Remember: Keep Sarah and Dennis as the only hosts, no action markers, and make it more natural and engaging."""
        
        response = enhancer_model.generate_content(enhance_prompt)
        enhanced_script_response = response.text
        
        # Parse enhanced script
        try:
            if "```json" in enhanced_script_response:
                json_start = enhanced_script_response.find("```json") + 7
                json_end = enhanced_script_response.find("```", json_start)
                enhanced_script = json.loads(enhanced_script_response[json_start:json_end].strip())
            elif "{" in enhanced_script_response:
                json_start = enhanced_script_response.find("{")
                json_end = enhanced_script_response.rfind("}") + 1
                enhanced_script = json.loads(enhanced_script_response[json_start:json_end])
            else:
                # Use original script if enhancement parsing fails
                enhanced_script = script_json
        except (json.JSONDecodeError, ValueError):
            enhanced_script = script_json
        
        # Save enhanced script
        enhanced_script_path = os.path.join(dirs['DATA'], "enhanced_podcast_script.json")
        with open(enhanced_script_path, 'w') as f:
            json.dump(enhanced_script, f, indent=2)
        
        # Step 5: Generate Audio
        if progress_callback:
            progress_callback("Generating audio segments...")
        
        # Convert dialogue to list of dicts
        dialogue_list = []
        for line in enhanced_script.get('dialogue', []):
            if isinstance(line, dict):
                dialogue_list.append({
                    'speaker': line.get('speaker', ''),
                    'text': line.get('text', '')
                })
        
        # Generate audio segments
        audio_files = audio_generator.generate_audio(dialogue_list)
        
        if progress_callback:
            progress_callback("Mixing final podcast...")
        
        # Mix audio
        final_podcast_path = podcast_mixer.mix_audio(audio_files)
        
        # Save audio metadata
        audio_meta = {
            "segment_files": audio_files,
            "final_podcast": final_podcast_path
        }
        audio_meta_path = os.path.join(dirs['DATA'], "audio_generation_meta.json")
        with open(audio_meta_path, 'w') as f:
            json.dump(audio_meta, f, indent=2)
        
        if progress_callback:
            progress_callback("Podcast generation complete!")
        
        return final_podcast_path
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error: {str(e)}")
        raise


# Streamlit UI
def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="AI Agents Podcast Generator",
        page_icon="🎙️",
        layout="wide"
    )
    
    st.title("🎙️ AI Agents Podcast Generator")
    st.markdown("Convert research papers into engaging podcast conversations using Google ADK agents.")
    
    # Initialize session state
    if 'podcast_path' not in st.session_state:
        st.session_state.podcast_path = None
    if 'status' not in st.session_state:
        st.session_state.status = None
    
    # Sidebar for file upload
    with st.sidebar:
        st.header("Upload PDF")
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
                if not os.getenv("GOOGLE_API_KEY") or not os.getenv("ELEVENLABS_API_KEY"):
                    st.error("Please set GOOGLE_API_KEY and ELEVENLABS_API_KEY in your .env file")
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
        st.info("👆 Upload a PDF file in the sidebar to get started!")
        
        st.markdown("""
        ### How it works:
        1. **Upload a PDF**: Select a research paper PDF file
        2. **Generate**: Click the "Generate Podcast" button
        3. **Listen**: Once generated, listen to your podcast using the audio player
        
        ### Features:
        - 🤖 AI-powered research analysis using Google ADK
        - 📝 Natural dialogue generation between two hosts
        - 🎙️ High-quality voice synthesis
        - 🎵 Professional audio mixing
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
