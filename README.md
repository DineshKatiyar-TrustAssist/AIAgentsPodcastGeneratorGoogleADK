# AI Agents Podcast Generator

An AI-powered system that automatically converts research papers into engaging podcast conversations using Google ADK (Agent Development Kit) agents, ElevenLabs text-to-speech, and intelligent script generation.

## Overview

This project uses Google ADK to transform academic research papers into natural, conversational podcasts. The system employs specialized AI agents that handle research analysis, script writing, enhancement, and audio generation to create professional-quality podcast content.

## Features

- **🎨 Streamlit Web UI**: User-friendly interface for uploading PDFs and listening to generated podcasts
- **📄 PDF Upload**: Easy drag-and-drop PDF upload functionality
- **🎧 Audio Player**: Built-in audio player to listen to generated podcasts directly in the browser
- **⬇️ Download Support**: Download generated podcasts as MP3 files
- **🤖 Automated Research Analysis**: Extracts key findings, methodology, implications, and limitations from research papers
- **🔍 Supporting Research Integration**: Finds and incorporates relevant supplementary materials and real-world context
- **💬 Natural Dialogue Generation**: Creates engaging conversations between two hosts (Sarah and Dennis)
- **✨ Script Enhancement**: Improves scripts with natural humor, analogies, and engaging banter
- **🎙️ High-Quality Audio Generation**: Uses ElevenLabs API for natural-sounding voice synthesis
- **🎵 Professional Audio Mixing**: Combines audio segments with proper normalization and transitions
- **📁 Organized Output Structure**: Automatically organizes outputs into timestamped directories

## Architecture

The system uses Google ADK with a sequential workflow of four specialized agents:

1. **Research Analyst Agent**: Analyzes research papers and creates comprehensive summaries using Gemini models
2. **Research Support Agent**: Finds supplementary materials and real-world context using Google Search
3. **Script Writer Agent**: Creates initial podcast scripts with natural dialogue
4. **Script Enhancer Agent**: Improves scripts for engagement and entertainment
5. **Audio Tools**: Generate and mix final podcast audio (not an agent, but tools used in the workflow)

## Installation

### Prerequisites

- Python 3.10 or higher
- API keys for:
  - Google API Key (for Gemini models via Google ADK)
  - ElevenLabs (for text-to-speech)
  - Voice IDs from ElevenLabs for the two hosts

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

3. Create a `.env` file in the project root with your API keys:
```env
GOOGLE_API_KEY=your_google_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
BEN_VOICE_ID=your_ben_voice_id
CLAUDIA_VOICE_ID=your_claudia_voice_id
```

**Getting API Keys:**
- **Google API Key**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey) or [Google Cloud Console](https://console.cloud.google.com/)
- **ElevenLabs API Key**: Sign up at [ElevenLabs](https://elevenlabs.io/) and get your API key from the dashboard
- **Voice IDs**: Create or select voices in your ElevenLabs account and use their voice IDs

## Usage

### Web UI (Recommended)

The easiest way to use the application is through the Streamlit web interface:

1. **Start the Streamlit app**:
```bash
streamlit run app.py
```

2. **Open your browser**: The app will automatically open at `http://localhost:8501`

3. **Upload a PDF**:
   - Use the file uploader in the sidebar
   - Select a research paper PDF file
   - Click "Generate Podcast"

4. **Wait for generation**: The system will process your PDF through multiple stages:
   - Loading PDF document
   - Initializing AI agents
   - Analyzing research paper
   - Finding supporting materials
   - Creating podcast script
   - Enhancing script
   - Generating audio
   - Mixing final podcast

5. **Listen to your podcast**: Once generated, the audio player will appear on the main page with:
   - Play/pause controls
   - Seek bar for navigation
   - Download button to save the MP3 file

### Command-Line Mode

For advanced users or automation, you can also use the command-line interface:

```bash
python app.py your_paper.pdf
```

The system will:
- Automatically copy the PDF to the `knowledge/` directory
- Create a timestamped output directory
- Generate paper summary, supporting research, and scripts
- Produce individual audio segments for each dialogue line
- Mix all segments into a final podcast file

## Streamlit UI Features

### Main Interface
- **Title and Description**: Clear indication of the application's purpose
- **Status Updates**: Real-time progress indicators during podcast generation
- **Audio Player**: Integrated audio player with full playback controls
- **Download Button**: One-click download of generated podcasts

### Sidebar
- **File Upload**: Drag-and-drop or click to upload PDF files
- **Generate Button**: Start the podcast generation process
- **Status Messages**: Success/error notifications

### Error Handling
- Validates API key configuration before processing
- Provides clear error messages for troubleshooting
- Handles file upload issues gracefully

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
- PDFs are automatically copied to `knowledge/` directory for processing
- Generated podcasts can be accessed via the web UI or file system

## Key Components

### Agents

- **Researcher**: PhD-level analyst specializing in breaking down complex papers
- **Research Support**: Finds current context and supporting materials
- **Script Writer**: Creates engaging technical podcast scripts
- **Script Enhancer**: Adds entertainment value while maintaining accuracy
- **Audio Generator**: Handles voice synthesis and audio production

### Tools

#### PodcastAudioGenerator
- Synthesizes speech using ElevenLabs API
- Supports multiple voice configurations
- Applies audio normalization and quality enhancements
- Generates individual audio segments for each dialogue line

#### PodcastMixer
- Combines audio segments into final podcast
- Applies crossfades and transitions
- Normalizes audio levels for consistent quality
- Exports in professional MP3 format

### Voice Configuration

The system supports configurable voice settings:
- **Stability**: Controls voice variation (0.0-1.0)
- **Similarity Boost**: Maintains voice consistency (0.0-1.0)
- **Style**: Expressiveness level (0.0-1.0)
- **Speaker Boost**: Enhances voice clarity

Default hosts:
- **Sarah**: Enthusiastic expert (uses CLAUDIA_VOICE_ID)
- **Dennis**: Engaged and curious co-host (uses BEN_VOICE_ID)

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
- Sample Rate: 48kHz
- Bitrate: 256k
- Normalization: Enabled
- Target Loudness: -14.0 LUFS

## Dependencies

- `google-adk`: Google Agent Development Kit for building AI agents
- `google-generativeai`: Google Generative AI SDK for Gemini models
- `elevenlabs`: Text-to-speech API client
- `pydub`: Audio processing library
- `pydantic`: Data validation
- `python-dotenv`: Environment variable management
- `streamlit`: Web UI framework
- `PyPDF2`: PDF text extraction library

## Project Structure

```
AIAgentsPodcastGenerator/
├── app.py                 # Main application with Streamlit UI and Google ADK agents
├── tools.py               # Audio generation and mixing tools
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── uploads/               # Temporary storage for uploaded PDFs
└── outputs/               # Generated content (timestamped)
    └── YYYYMMDD_HHMMSS/
        ├── data/          # JSON metadata files
        ├── segments/      # Individual audio segments
        └── podcast/       # Final mixed podcast
```

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
- Generates natural-sounding voices with proper intonation
- Applies professional audio processing
- Creates smooth transitions between speakers
- Ensures consistent audio quality throughout

## Workflow

1. **PDF Upload**: User uploads a research paper PDF via Streamlit UI
2. **Text Extraction**: PDF text is extracted using PyPDF2
3. **Research Analysis**: Research Analyst agent (Google ADK) extracts key information using Gemini
4. **Supporting Research**: Research Support agent finds relevant context using Google Search
5. **Script Creation**: Script Writer agent creates initial podcast script
6. **Script Enhancement**: Script Enhancer agent improves engagement and flow
7. **Audio Generation**: Audio tools create voice segments for each dialogue line using ElevenLabs
8. **Audio Mixing**: PodcastMixer combines segments into final podcast
9. **Output**: Podcast is available in the UI for playback and download

## Notes

- The system requires valid API keys for Google ADK (Gemini) and ElevenLabs
- Voice IDs must be obtained from ElevenLabs
- PDF files are automatically processed - text is extracted directly from uploaded files
- Output directories are automatically created with timestamps
- All intermediate data is saved as JSON for review and debugging
- The Streamlit UI provides real-time progress updates during generation
- Generated podcasts are stored in timestamped directories for easy organization
- Google ADK agents use Gemini models which provide high-quality responses
- The system uses Google Search tool for finding supporting research materials

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure `GOOGLE_API_KEY` and `ELEVENLABS_API_KEY` are set in your `.env` file
2. **PDF Processing Errors**: Ensure the PDF is not corrupted and contains extractable text
3. **Generation Fails**: Check the console/logs for detailed error messages. Verify Google API quota limits
4. **Audio Player Not Showing**: Verify that the podcast file was successfully generated in `outputs/`
5. **Google ADK Import Errors**: Ensure `google-adk` is properly installed: `pip install google-adk`

### Getting Help

- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify API keys are correctly set in `.env` file (especially `GOOGLE_API_KEY`)
- Ensure you have sufficient API quotas for Google Gemini and ElevenLabs
- Check Google ADK documentation: https://google.github.io/adk-docs/
- Verify your Google API key has access to Gemini models

## License

[Add your license information here]

## Contributing

[Add contribution guidelines if applicable]
