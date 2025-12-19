# AI Agents Podcast Generator

An AI-powered system that automatically converts research papers into engaging podcast conversations using Google ADK (Agent Development Kit) multi-agent system, Google TTS (Text-to-Speech), and intelligent script generation.

## Overview

This project uses Google ADK to transform academic research papers into natural, conversational podcasts. The system employs specialized AI agents that handle research analysis, script writing, enhancement, and audio generation to create professional-quality podcast content.

## Features

- **🔐 User Authentication**: Secure email-based signup with email verification and password protection
- **🎨 Streamlit Web UI**: User-friendly interface for uploading PDFs and listening to generated podcasts
- **📄 PDF Upload**: Easy drag-and-drop PDF upload functionality
- **🎧 Audio Player**: Built-in audio player to listen to generated podcasts directly in the browser
- **⬇️ Download Support**: Download generated podcasts as MP3 files
- **🤖 Automated Research Analysis**: Extracts key findings, methodology, implications, and limitations from research papers
- **🔍 Supporting Research Integration**: Finds and incorporates relevant supplementary materials and real-world context
- **💬 Natural Dialogue Generation**: Creates engaging conversations between two hosts (Sarah and Dennis)
- **✨ Script Enhancement**: Improves scripts with natural humor, analogies, and engaging banter
- **🎙️ High-Quality Audio Generation**: Uses Google TTS (gemini-2.5-flash-preview-tts) for natural-sounding voice synthesis
- **🎵 Professional Audio Mixing**: Combines audio segments with proper normalization and transitions
- **📁 Organized Output Structure**: Automatically organizes outputs into timestamped directories

## Architecture

The system uses Google ADK with a **SequentialAgent** workflow that orchestrates five specialized agents in order:

1. **Research Analyst Agent**: Analyzes research papers and creates comprehensive summaries using Gemini models
   - Model: `gemini-2.0-flash-exp`
   - Output: Structured JSON summary with findings, methodology, implications, etc.
   
2. **Research Support Agent**: Finds supplementary materials and real-world context using knowledge base
   - Model: `gemini-2.0-flash-exp`
   - Output: Supporting research materials and context
   
3. **Script Writer Agent**: Creates initial podcast scripts with natural dialogue
   - Model: `gemini-2.0-flash-exp`
   - Output: JSON script with dialogue between Sarah and Dennis
   
4. **Script Enhancer Agent**: Improves scripts for engagement and entertainment
   - Model: `gemini-2.0-flash-exp`
   - Output: Enhanced JSON script with natural reactions and flow
   
5. **Audio Generator Agent**: Generates audio segments using Google TTS via FunctionTool
   - Model: `gemini-2.0-flash-exp`
   - Tools: `FunctionTool(generate_audio_segments)`
   - Output: Audio generation result with final podcast path

**Workflow Pattern**: Sequential - Each agent runs in order, with outputs passed to the next agent via `{output_key}` placeholders in instructions.

## Installation

### Prerequisites

- Python 3.10 or higher
- Google API Key (entered in the application UI after login)
- Gmail account for sending verification emails (with App Password)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd AIAgentsPodcastGenerator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:
```bash
# Gmail SMTP for sending verification emails
GMAIL_SENDER_EMAIL="your-email@gmail.com"
GMAIL_APP_PASSWORD="your-16-char-app-password"

# Admin notification email (receives alerts for new signups)
ADMIN_NOTIFICATION_EMAIL="admin@example.com"

# Application URL (for email verification links)
APP_BASE_URL="http://localhost:8501"
```

**Getting Gmail App Password:**
1. Go to your Google Account > Security
2. Enable 2-Step Verification if not already enabled
3. Go to App passwords (under 2-Step Verification)
4. Generate a new app password for "Mail"
5. Use the 16-character password in `GMAIL_APP_PASSWORD`

**Getting Your Google API Key:**
- Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- The API key is used for both Gemini models (for agents) and Google TTS (for audio generation)
- You'll enter this key in the Streamlit UI after logging in

**Voice Configuration (Optional):**
- Voice names can be set via environment variables if desired:
  - **SARAH_VOICE_NAME**: Google TTS prebuilt voice name for Sarah (default: "Kore" - female voice)
  - **DENNIS_VOICE_NAME**: Google TTS prebuilt voice name for Dennis (default: "Puck" - male voice)
- Available voices include: Kore, Puck, Charon, Fenrir, and others

## Usage

### Web UI (Recommended)

The easiest way to use the application is through the Streamlit web interface:

1. **Start the Streamlit app**:
```bash
streamlit run app.py
```

2. **Open your browser**: The app will automatically open at `http://localhost:8501`

3. **Create an Account** (First-time users):
   - Click "Create Account" on the login page
   - Enter your email address
   - Check your email for a verification link
   - Click the verification link
   - Create a secure password (min 8 chars, uppercase, lowercase, digit, special char)

4. **Sign In** (Returning users):
   - Enter your email and password
   - Click "Sign In"
   - Use "Forgot Password?" if you need to reset your password

5. **Enter API Key** (Required after login):
   - In the sidebar, enter your Google API Key in the "🔑 API Configuration" section
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - The application will not work without a valid API key
   - Your key is stored only in your browser session (not saved to disk)

6. **Upload a PDF**:
   - Use the file uploader in the sidebar
   - Select a research paper PDF file
   - Click "Generate Podcast"

7. **Wait for generation**: The system will process your PDF through multiple stages:
   - Loading PDF document
   - Initializing AI agents
   - Analyzing research paper
   - Finding supporting materials
   - Creating podcast script
   - Enhancing script
   - Generating audio
   - Mixing final podcast

8. **Listen to your podcast**: Once generated, the audio player will appear on the main page with:
   - Play/pause controls
   - Seek bar for navigation
   - Download button to save the MP3 file

### Command-Line Mode

For advanced users or automation, you can also use the command-line interface:

```bash
python app.py your_paper.pdf
```

The system will:
- Extract text directly from the PDF using PyPDF2
- Create a timestamped output directory
- Run the multi-agent workflow sequentially:
  1. Research Analyst creates paper summary
  2. Research Support finds supplementary materials
  3. Script Writer creates initial podcast script
  4. Script Enhancer improves the script
  5. Audio Generator calls FunctionTool to generate audio
- Produce individual audio segments for each dialogue line using Google TTS
- Mix all segments into a final podcast file

## Streamlit UI Features

### Main Interface
- **Title and Description**: Clear indication of the application's purpose
- **Status Updates**: Real-time progress indicators during podcast generation
- **Audio Player**: Integrated audio player with full playback controls
- **Download Button**: One-click download of generated podcasts

### Sidebar
- **API Configuration**: Required input field for Google API Key
  - Password-protected input for security
  - Key is stored only in browser session (not saved to disk)
  - Application stops if key is not provided
- **File Upload**: Drag-and-drop or click to upload PDF files
- **Generate Button**: Start the podcast generation process
- **Status Messages**: Success/error notifications

### Error Handling
- **API Key Validation**: Application requires API key input and stops if not provided
- **Clear Error Messages**: Provides detailed error messages for troubleshooting
- **File Upload Issues**: Handles file upload problems gracefully
- **No .env Required**: Application does not use API keys from .env file - must be entered in UI

## Output Structure

Each run creates a timestamped directory under `outputs/`:

```
outputs/YYYYMMDD_HHMMSS/
├── data/
│   ├── paper_summary.json
│   ├── supporting_research.json
│   ├── podcast_script.json
│   ├── enhanced_podcast_script.json
│   └── audio_generation_meta.json
├── segments/
│   ├── 000_Sarah.mp3
│   ├── 001_Dennis.mp3
│   └── ...
└── podcast/
    └── podcast_final.mp3
```

Additionally:
- Uploaded PDFs are temporarily stored in `uploads/` directory
- PDF text is extracted directly from uploaded files (no knowledge directory needed)
- Generated podcasts can be accessed via the web UI or file system

## Key Components

### Agents

- **Research Analyst**: PhD-level analyst specializing in breaking down complex papers
- **Research Support**: Finds current context and supporting materials using knowledge base
- **Script Writer**: Creates engaging technical podcast scripts
- **Script Enhancer**: Adds entertainment value while maintaining accuracy
- **Audio Generator**: Generates audio using Google TTS via FunctionTool integration

### Tools

#### PodcastAudioGenerator
- Synthesizes speech using Google TTS (gemini-2.5-flash-preview-tts model)
- Uses single-speaker TTS per segment with correct voice assignment
- Supports Google TTS prebuilt voices (Kore, Puck, Charon, Fenrir, etc.)
- Applies audio normalization and quality enhancements
- Generates individual audio segments for each dialogue line
- Converts PCM audio from Google TTS to MP3 format

#### PodcastMixer
- Combines audio segments into final podcast
- Applies crossfades and transitions
- Normalizes audio levels for consistent quality
- Exports in professional MP3 format

### Voice Configuration

The system uses Google TTS prebuilt voices:
- **Voice Names**: Configurable via environment variables
- **Default Voices**:
  - **Sarah**: Puck (female voice) - Enthusiastic expert
  - **Dennis**: Kore (male voice) - Engaged and curious co-host

**Available Google TTS Voices:**
- Kore (male)
- Puck (female)
- Charon (male)
- Fenrir (male)
- And others - check Google TTS documentation for full list

**Customization:**
Set `SARAH_VOICE_NAME` and `DENNIS_VOICE_NAME` as environment variables (optional) to use different voices. Defaults are used if not specified.

## Configuration

### LLM Models

The system uses Google Gemini models via Google ADK:
- **Model**: `gemini-2.0-flash-exp` (used by all agents)
- All agents are configured with specific instructions tailored to their roles
- The framework handles model configuration and API interactions automatically
- Temperature and other parameters are managed by the ADK framework

### Audio Settings

Default audio configuration:
- Format: MP3
- Sample Rate: 24kHz (Google TTS default), upsampled to 48kHz for final output
- Bitrate: 256k
- Normalization: Enabled
- Target Loudness: -14.0 LUFS
- Google TTS Model: gemini-2.5-flash-preview-tts

## Dependencies

- `google-adk`: Google Agent Development Kit for building AI agents
- `google-genai`: Google Generative AI SDK for Gemini models and TTS
- `google-generativeai`: Google Generative AI SDK (legacy support)
- `pydub`: Audio processing library for audio processing and conversion
- `pydantic`: Data validation
- `python-dotenv`: Environment variable management
- `streamlit`: Web UI framework
- `PyPDF2`: PDF text extraction library
- `bcrypt`: Secure password hashing
- `email-validator`: Email address validation

## Project Structure

```
AIAgentsPodcastGenerator/
├── app.py                 # Main application with Streamlit UI and Google ADK agents
├── tools.py               # Audio generation and mixing tools
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (Gmail SMTP, admin email)
├── .gitignore             # Git ignore file
├── Dockerfile             # Docker configuration for deployment
├── .dockerignore          # Files excluded from Docker build
├── cloudbuild.yaml        # Google Cloud Build configuration
├── app.yaml               # App Engine configuration
├── DEPLOYMENT.md          # Deployment guide
├── auth/                  # Authentication module
│   ├── __init__.py        # Module exports
│   ├── database.py        # SQLite database operations
│   ├── models.py          # Pydantic models for users/tokens
│   ├── security.py        # Password hashing, token generation
│   ├── email_service.py   # Gmail SMTP email service
│   └── utils.py           # URL generation helpers
├── data/                  # Application data
│   └── auth.db            # SQLite database (auto-created)
├── uploads/               # Temporary storage for uploaded PDFs
└── outputs/               # Generated content (timestamped)
    └── YYYYMMDD_HHMMSS/
        ├── data/          # JSON metadata files
        ├── segments/      # Individual audio segments
        └── podcast/       # Final mixed podcast
```

**Note**: The `.env` file is required for email functionality. Users enter their Google API key in the Streamlit UI after logging in.

## Features in Detail

### Research Analysis
- Extracts title, findings, methodology, implications, limitations, and future work
- Creates structured summaries using Pydantic models
- Maintains accuracy while making content accessible

### Supporting Research
- Searches for recent developments and real-world applications
- Finds academic discussions, industry reports, and case studies
- Provides different perspectives and cross-disciplinary connections

### Script Generation
- Creates natural dialogue between two hosts
- Clearly attributes sources (paper vs. supplementary research)
- Includes friendly disagreements and collaborative discussions
- Maintains educational value while being engaging

### Script Enhancement
- Adds natural reactions and verbal expressions
- Includes relatable analogies and examples
- Balances technical depth with accessibility
- Preserves accuracy while improving entertainment value

### Audio Production
- Audio Generator Agent uses FunctionTool to call audio generation function
- Generates natural-sounding voices using Google TTS with proper intonation
- Uses single-speaker TTS per segment with correct voice assignment (Sarah → Puck, Dennis → Kore)
- Applies professional audio processing and normalization
- Converts PCM audio from Google TTS to MP3 format
- Creates smooth transitions between speakers
- Ensures consistent audio quality throughout

## Workflow

1. **PDF Upload**: User uploads a research paper PDF via Streamlit UI
2. **Text Extraction**: PDF text is extracted using PyPDF2
3. **Research Analysis**: Research Analyst agent (Google ADK) extracts key information using Gemini
4. **Supporting Research**: Research Support agent finds relevant context using knowledge base
5. **Script Creation**: Script Writer agent creates initial podcast script
6. **Script Enhancement**: Script Enhancer agent improves engagement and flow
7. **Audio Generation**: Audio Generator agent calls FunctionTool to generate voice segments for each dialogue line using Google TTS
8. **Audio Mixing**: PodcastMixer combines segments into final podcast
9. **Output**: Podcast is available in the UI for playback and download

## Notes

- **API Key Required**: The system requires a valid Google API Key entered in the Streamlit UI
  - The API key is NOT read from .env file - users must enter it in the application
  - Key is stored only in browser session (not persisted to disk)
  - Required for both Gemini models (agents) and Google TTS (audio generation)
- Voice names are Google TTS prebuilt voices (no separate voice creation needed)
- PDF files are automatically processed - text is extracted directly from uploaded files using PyPDF2
- Output directories are automatically created with timestamps
- All intermediate data is saved as JSON for review and debugging
- The Streamlit UI provides real-time progress updates during generation
- Generated podcasts are stored in timestamped directories for easy organization
- Google ADK agents use Gemini models (gemini-2.0-flash-exp) which provide high-quality responses
- The system uses a multi-agent sequential workflow with 5 specialized agents
- Audio generation uses Google TTS via FunctionTool integration with the AudioGenerator agent
- The system uses InMemoryRunner with run_debug() for proper async execution and function call handling

## Troubleshooting

### Common Issues

1. **API Key Errors**: 
   - Ensure you enter your Google API Key in the Streamlit UI sidebar
   - The application does NOT use API keys from .env file
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Application will stop and show an error if API key is not provided
2. **PDF Processing Errors**: Ensure the PDF is not corrupted and contains extractable text
3. **Generation Fails**: Check the console/logs for detailed error messages. Verify Google API quota limits
4. **Audio Player Not Showing**: Verify that the podcast file was successfully generated in `outputs/`
5. **Google ADK Import Errors**: Ensure `google-adk` is properly installed: `pip install google-adk`

### Getting Help

- Check that all dependencies are installed: `pip install -r requirements.txt`
- **Enter your Google API Key in the Streamlit UI** (required - not from .env file)
- Ensure you have sufficient API quotas for Google Gemini and Google TTS
- Check that your Google API key has access to both Gemini models and TTS features
- Check Google ADK documentation: https://google.github.io/adk-docs/
- Verify your Google API key has access to Gemini models
- If the application stops with an API key error, check that you've entered the key in the sidebar

## Deployment

This application can be deployed to Google Cloud Platform using Docker. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy to Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/podcast-generator
gcloud run deploy podcast-generator \
    --image gcr.io/$PROJECT_ID/podcast-generator \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8501 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600
```

**Note**: The application requires users to enter their Google API key in the UI. For production deployments, you may want to set up authentication or use environment variables, but the default behavior is user-provided keys in the UI.

### Docker Support

The application includes:
- **Dockerfile**: For containerizing the application
- **.dockerignore**: Excludes unnecessary files from Docker build
- **cloudbuild.yaml**: Cloud Build configuration for automated deployments
- **app.yaml**: App Engine configuration (alternative deployment)
- **DEPLOYMENT.md**: Comprehensive deployment guide

## License

[Add your license information here]

## Contributing

[Add contribution guidelines if applicable]
