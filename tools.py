"""
Audio generation and mixing tools for podcast production.
Using Google TTS models.
"""
import os
import wave
import warnings
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydub import AudioSegment
from pydantic import Field, BaseModel, ConfigDict
from google import genai
from google.genai import types

# Suppress function_call warnings from Google TTS
warnings.filterwarnings('ignore', message='.*non-text parts in the response.*')
warnings.filterwarnings('ignore', message='.*function_call.*')


class VoiceConfig(BaseModel):
    """Voice configuration settings for Google TTS."""
    voice_name: str = Field(..., description="Google TTS prebuilt voice name (e.g., 'Kore', 'Puck', 'Charon', etc.)")


class AudioConfig(BaseModel):
    """Audio processing configuration."""
    format: str = "mp3"
    sample_rate: int = 24000  # Google TTS default
    channels: int = 1
    bitrate: str = "256k"
    normalize: bool = True
    target_loudness: float = -14.0
    compression_ratio: float = 2.0


class Dialogue(BaseModel):
    """Dialogue for the podcast audio generation tool."""
    speaker: str
    text: str


class PodcastAudioGenerator:
    """
    Podcast audio generation tool using Google TTS.
    Synthesizes podcast voices using Google's multi-speaker TTS model.
    """
    
    def __init__(self, output_dir: str = "output/audio-files"):
        """
        Initialize the audio generator.
        
        Args:
            output_dir: Directory to save generated audio files
        """
        # Initialize Google genai client
        # API key can be passed or read from GOOGLE_API_KEY environment variable
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            # Try without explicit key (may be set elsewhere)
            try:
                self.client = genai.Client()
            except Exception:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
        self.voice_configs: Dict[str, VoiceConfig] = {}
        self.audio_config = AudioConfig()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def add_voice(
        self, 
        name: str, 
        voice_name: str,
        config: Optional[VoiceConfig] = None
    ) -> None:
        """
        Add a voice configuration.
        
        Args:
            name: Name of the speaker (e.g., "Sarah", "Dennis")
            voice_name: Google TTS prebuilt voice name (e.g., "Kore", "Puck")
            config: Optional voice configuration (will use voice_name from parameter if not provided)
        """
        if config:
            self.voice_configs[name] = config
        else:
            self.voice_configs[name] = VoiceConfig(voice_name=voice_name)

    def _save_wave_file(self, filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2):
        """Save PCM audio data to a WAV file."""
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    def generate_audio(self, dialogue: List[Dict[str, str]]) -> List[str]:
        """
        Generate audio files for each script segment using Google TTS.
        
        Args:
            dialogue: List of dialogue dictionaries with 'speaker' and 'text' keys
            
        Returns:
            List of generated audio file paths
        """
        audio_files = []
        
        # Use single-speaker TTS for each segment
        # Get voice mappings for Sarah and Dennis
        sarah_voice_config = self.voice_configs.get("Sarah")
        dennis_voice_config = self.voice_configs.get("Dennis")
        
        if not sarah_voice_config or not dennis_voice_config:
            raise ValueError("Both Sarah and Dennis voice configs must be set")
        
        # Create voice name mapping
        voice_mapping = {
            "Sarah": sarah_voice_config.voice_name,
            "Dennis": dennis_voice_config.voice_name
        }
        
        print(f"Voice mapping - Sarah: {voice_mapping['Sarah']}, Dennis: {voice_mapping['Dennis']}")
        
        for index, segment in enumerate(dialogue):
            speaker = segment.get('speaker', '').strip()
            text = segment.get('text', '').strip()
            
            if not speaker or not text:
                print(f"Skipping segment {index}: missing speaker or text")
                continue

            if speaker not in voice_mapping:
                print(f"Skipping unknown speaker: {speaker}")
                continue
            
            # Get the correct voice for this speaker
            voice_name = voice_mapping[speaker]
            
            print(f"Processing segment {index}: {speaker} -> {voice_name}")

            try:
                # Create prompt - simple format that TTS can understand
                prompt = f"{speaker}: {text}"
                
                # Create audio config with the correct voice for this speaker
                audio_config = types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    )
                )
                
                # Generate audio using Google TTS (single speaker)
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-preview-tts",
                    contents=prompt,
                    config=audio_config,
                )
                
                # Extract audio data from response
                audio_data = None
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                audio_data = part.inline_data.data
                                break
                
                if not audio_data:
                    raise ValueError("No audio data in response")
                
                # Save as WAV first (Google TTS returns PCM)
                wav_filename = f"{self.output_dir}/{index:03d}_{speaker}.wav"
                self._save_wave_file(wav_filename, audio_data)
                
                # Convert to MP3 and normalize
                audio = AudioSegment.from_wav(wav_filename)
                
                # Normalize audio
                if self.audio_config.normalize:
                    audio = audio.normalize()
                    audio = audio + 4  # Slight boost
                
                # Export as MP3
                mp3_filename = f"{self.output_dir}/{index:03d}_{speaker}.mp3"
                audio.export(
                    mp3_filename,
                    format="mp3",
                    bitrate=self.audio_config.bitrate,
                    parameters=["-ar", str(self.audio_config.sample_rate)]
                )
                
                # Remove temporary WAV file
                if os.path.exists(wav_filename):
                    os.remove(wav_filename)
                
                audio_files.append(mp3_filename)
                print(f'Audio content written to file "{mp3_filename}"')

            except Exception as e:
                print(f"Error processing segment {index}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        return sorted(audio_files)


class PodcastMixer:
    """
    Enhanced audio mixing tool for podcast production.
    Mixes multiple audio files with effects into final podcast.
    """
    
    def __init__(self, output_dir: str = "output/podcast"):
        """
        Initialize the podcast mixer.
        
        Args:
            output_dir: Directory to save the final podcast
        """
        self.audio_config = AudioConfig()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def mix_audio(
        self,
        audio_files: List[str],
        crossfade: int = 50
    ) -> str:
        """
        Mix multiple audio files into a final podcast.
        
        Args:
            audio_files: List of audio file paths to mix
            crossfade: Crossfade duration in milliseconds
            
        Returns:
            Path to the final mixed podcast file
        """
        if not audio_files:
            raise ValueError("No audio files provided to mix")

        try:
            mixed = AudioSegment.from_file(audio_files[0])
            for audio_file in audio_files[1:]:
                next_segment = AudioSegment.from_file(audio_file)
                # Add silence and use crossfade
                silence = AudioSegment.silent(duration=200)
                next_segment = silence + next_segment
                mixed = mixed.append(next_segment, crossfade=crossfade)

            # Simplified output path handling
            output_file = os.path.join(self.output_dir, "podcast_final.mp3")
            
            mixed.export(
                output_file,
                format="mp3",
                parameters=[
                    "-q:a", "0",  # Highest quality
                    "-ar", "48000"  # Professional sample rate
                ]
            )

            print(f"Successfully mixed podcast to: {output_file}")
            return output_file

        except Exception as e:
            print(f"Error mixing podcast: {str(e)}")
            raise
