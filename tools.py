"""
Audio generation and mixing tools for podcast production.
Using Google ADK framework.
"""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydub import AudioSegment
from pydantic import Field, BaseModel, ConfigDict
from elevenlabs.client import ElevenLabs


class VoiceConfig(BaseModel):
    """Voice configuration settings."""
    stability: float = 0.45
    similarity_boost: float = 0.85
    style: float = 0.65
    use_speaker_boost: bool = True
    model_id: str = "eleven_multilingual_v2"
    output_format: str = "mp3_44100_128"
    apply_text_normalization: str = "auto"


class AudioConfig(BaseModel):
    """Audio processing configuration."""
    format: str = "mp3"
    sample_rate: int = 48000
    channels: int = 2
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
    Enhanced podcast audio generation tool for Google ADK.
    Synthesizes podcast voices using ElevenLabs API.
    """
    
    def __init__(self, output_dir: str = "output/audio-files"):
        """
        Initialize the audio generator.
        
        Args:
            output_dir: Directory to save generated audio files
        """
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_configs: Dict[str, Dict] = {}
        self.audio_config = AudioConfig()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def add_voice(
        self, 
        name: str, 
        voice_id: str, 
        config: Optional[VoiceConfig] = None
    ) -> None:
        """
        Add a voice configuration.
        
        Args:
            name: Name of the speaker
            voice_id: ElevenLabs voice ID
            config: Optional voice configuration
        """
        self.voice_configs[name] = {
            "voice_id": voice_id,
            "config": config or VoiceConfig()
        }

    def generate_audio(self, dialogue: List[Dict[str, str]]) -> List[str]:
        """
        Generate audio files for each script segment.
        
        Args:
            dialogue: List of dialogue dictionaries with 'speaker' and 'text' keys
            
        Returns:
            List of generated audio file paths
        """
        audio_files = []
        
        for index, segment in enumerate(dialogue):
            speaker = segment.get('speaker', '').strip()
            text = segment.get('text', '').strip()
            
            if not speaker or not text:
                print(f"Skipping segment {index}: missing speaker or text")
                continue

            voice_config = self.voice_configs.get(speaker)
            if not voice_config:
                print(f"Skipping unknown speaker: {speaker}")
                continue

            try:
                audio_generator = self.client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_config["voice_id"],
                    model_id=voice_config['config'].model_id,
                    output_format=voice_config['config'].output_format,
                    voice_settings={
                        "stability": voice_config['config'].stability,
                        "similarity_boost": voice_config['config'].similarity_boost,
                        "style": voice_config['config'].style,
                        "use_speaker_boost": voice_config['config'].use_speaker_boost
                    }
                )

                # Convert generator to bytes
                audio_bytes = b''.join(chunk for chunk in audio_generator)

                filename = f"{self.output_dir}/{index:03d}_{speaker}.{self.audio_config.format}"
                with open(filename, "wb") as out:
                    out.write(audio_bytes)

                # Basic audio normalization
                if self.audio_config.normalize:
                    audio = AudioSegment.from_file(filename)
                    normalized = audio.normalize()
                    normalized = normalized + 4  # Slight boost
                    
                    normalized.export(
                        filename,
                        format=self.audio_config.format,
                        bitrate=self.audio_config.bitrate,
                        parameters=["-ar", str(self.audio_config.sample_rate)]
                    )

                audio_files.append(filename)
                print(f'Audio content written to file "{filename}"')

            except Exception as e:
                print(f"Error processing segment {index}: {str(e)}")
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
