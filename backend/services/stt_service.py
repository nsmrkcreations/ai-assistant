"""
Speech-to-Text Service using Whisper.cpp
"""

import asyncio
import logging
import tempfile
import subprocess
import os
import platform
import zipfile
from pathlib import Path
from typing import Optional
import wave
import io
import aiohttp
import aiofiles

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class STTService:
    """Speech-to-Text service using Whisper.cpp"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = config.models.stt_model
        self.whisper_path = self._find_whisper_executable()
        self.model_path = None
        
    async def start(self):
        """Start the STT service"""
        try:
            if not self.whisper_path:
                self.logger.warning("Whisper.cpp executable not found")
                return  # Don't raise exception, just warn
            
            # Try to download model if not available
            try:
                await self._ensure_model_available()
                self.logger.info(f"STT Service started with model: {self.model}")
            except Exception as model_error:
                self.logger.warning(f"Could not download STT model: {model_error}")
                # Don't raise exception, service can still report status
            
        except Exception as e:
            self.logger.error(f"Failed to start STT service: {e}")
            # Don't raise exception to allow graceful degradation
    
    async def stop(self):
        """Stop the STT service"""
        self.logger.info("STT Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            if self.whisper_path and self.model_path and Path(self.model_path).exists():
                return ComponentStatus(
                    name="stt_service",
                    status=ServiceStatus.HEALTHY,
                    version=self.model,
                    details={
                        "model": self.model,
                        "model_path": str(self.model_path),
                        "whisper_path": str(self.whisper_path)
                    }
                )
            else:
                return ComponentStatus(
                    name="stt_service",
                    status=ServiceStatus.DEGRADED,
                    error="Whisper executable or model not found"
                )
                
        except Exception as e:
            return ComponentStatus(
                name="stt_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio data to text"""
        try:
            if not self.whisper_path or not self.model_path:
                return "Speech recognition not available"
            
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Convert to proper WAV format if needed
                processed_audio_path = await self._process_audio(temp_file_path)
                
                # Run whisper transcription
                transcription = await self._run_whisper(processed_audio_path)
                
                # Clean up transcription
                clean_transcription = self._clean_transcription(transcription)
                
                return clean_transcription if clean_transcription else "No speech detected"
                
            finally:
                # Cleanup temporary files
                try:
                    os.unlink(temp_file_path)
                    if processed_audio_path != temp_file_path:
                        os.unlink(processed_audio_path)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error transcribing audio: {e}")
            return f"Transcription error: {str(e)}"
    
    async def _ensure_model_available(self):
        """Download model if not available"""
        model_dir = self.config.get_data_path("models")
        model_dir.mkdir(exist_ok=True)
        
        self.model_path = model_dir / f"ggml-{self.model}.bin"
        
        if not self.model_path.exists():
            self.logger.info(f"Downloading Whisper model: {self.model}")
            await self._download_model()
        
        # Ensure whisper.cpp executable is available
        if not self.whisper_path:
            await self._ensure_whisper_executable()
    
    async def _download_model(self):
        """Download Whisper model"""
        model_url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{self.model}.bin"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(model_url, allow_redirects=True) as response:
                    if response.status == 200:
                        async with aiofiles.open(self.model_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        self.logger.info(f"Model downloaded: {self.model_path}")
                    else:
                        raise Exception(f"Failed to download model: HTTP {response.status}")
        
        except Exception as e:
            self.logger.error(f"Failed to download model: {e}")
            # Try to download whisper.cpp executable if model download fails
            await self._ensure_whisper_executable()
            raise
    
    async def _ensure_whisper_executable(self):
        """Download whisper.cpp executable if not found"""
        if self.whisper_path and self.whisper_path.exists():
            return
        
        whisper_dir = self.config.get_data_path("whisper")
        whisper_dir.mkdir(exist_ok=True)
        
        system = platform.system().lower()
        
        if system == "windows":
            # Download pre-built Windows binary
            url = "https://github.com/ggerganov/whisper.cpp/releases/latest/download/whisper-bin-Win32.zip"
            executable_name = "main.exe"
        elif system == "darwin":
            # Download pre-built macOS binary
            url = "https://github.com/ggerganov/whisper.cpp/releases/latest/download/whisper-bin-Darwin.zip"
            executable_name = "main"
        else:
            # For Linux, we'll need to build from source or use a different approach
            self.logger.warning("Whisper.cpp auto-download not supported on Linux. Please install manually.")
            return
        
        try:
            self.logger.info(f"Downloading Whisper.cpp for {system}")
            
            zip_path = whisper_dir / "whisper.zip"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        async with aiofiles.open(zip_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        # Extract the zip file
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(whisper_dir)
                        
                        # Find the executable
                        for file in whisper_dir.rglob(executable_name):
                            if file.is_file():
                                self.whisper_path = file
                                # Make executable on Unix systems
                                if system != "windows":
                                    os.chmod(file, 0o755)
                                break
                        
                        # Clean up zip file
                        os.unlink(zip_path)
                        
                        if self.whisper_path:
                            self.logger.info(f"Whisper.cpp downloaded: {self.whisper_path}")
                        else:
                            raise Exception("Executable not found in downloaded package")
                    
                    else:
                        raise Exception(f"Failed to download: HTTP {response.status}")
        
        except Exception as e:
            self.logger.error(f"Failed to download Whisper.cpp: {e}")
            raise
    
    async def _process_audio(self, audio_path: str) -> str:
        """Process audio file to ensure it's in the right format for Whisper"""
        try:
            # Check if the audio is already in WAV format
            with wave.open(audio_path, 'rb') as wav_file:
                # Check if it's the right format (16kHz, mono, 16-bit)
                if (wav_file.getframerate() == 16000 and 
                    wav_file.getnchannels() == 1 and 
                    wav_file.getsampwidth() == 2):
                    return audio_path
        except:
            pass
        
        # Convert audio using ffmpeg if available
        output_path = audio_path.replace('.wav', '_processed.wav')
        
        try:
            # Try to use ffmpeg for conversion
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',      # mono
                '-c:a', 'pcm_s16le',  # 16-bit PCM
                '-y',            # overwrite output
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return output_path
            else:
                self.logger.warning(f"FFmpeg conversion failed: {stderr.decode()}")
                return audio_path  # Return original if conversion fails
        
        except FileNotFoundError:
            self.logger.warning("FFmpeg not found, using original audio file")
            return audio_path
        except Exception as e:
            self.logger.warning(f"Audio processing failed: {e}")
            return audio_path
    
    async def _run_whisper(self, audio_path: str) -> str:
        """Run Whisper.cpp transcription"""
        if not self.whisper_path or not self.whisper_path.exists():
            raise Exception("Whisper.cpp executable not found")
        
        if not self.model_path or not self.model_path.exists():
            raise Exception("Whisper model not found")
        
        try:
            cmd = [
                str(self.whisper_path),
                '-m', str(self.model_path),
                '-f', audio_path,
                '--output-txt',
                '--no-timestamps',
                '--threads', '4',
                '--processors', '1'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.whisper_path.parent
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=30.0  # 30 second timeout
            )
            
            if process.returncode == 0:
                # Try to read from output file first
                txt_file = Path(audio_path).with_suffix('.txt')
                if txt_file.exists():
                    transcription = txt_file.read_text(encoding='utf-8').strip()
                    txt_file.unlink(missing_ok=True)
                    return transcription
                
                # Fallback to stdout
                transcription = stdout.decode('utf-8').strip()
                
                # Remove any whisper.cpp specific output formatting
                lines = transcription.split('\n')
                # Find the actual transcription (usually the last non-empty line)
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith('[') and not line.startswith('whisper'):
                        return line
                
                return transcription  # Fallback to full output
            else:
                error_msg = stderr.decode('utf-8')
                raise Exception(f"Whisper.cpp failed: {error_msg}")
        
        except asyncio.TimeoutError:
            raise Exception("Whisper transcription timed out")
        except Exception as e:
            self.logger.error(f"Whisper execution failed: {e}")
            raise
    
    def _find_whisper_executable(self) -> Optional[Path]:
        """Find whisper.cpp executable"""
        # Check if we have a local whisper executable
        whisper_dir = self.config.get_data_path("whisper")
        
        if platform.system() == "Windows":
            executable_name = "main.exe"
        else:
            executable_name = "main"
        
        local_whisper = whisper_dir / executable_name
        if local_whisper.exists():
            return local_whisper
        
        # Common locations for whisper.cpp
        possible_paths = [
            Path("whisper.cpp/main"),
            Path("whisper.cpp/main.exe"),
            Path("/usr/local/bin/whisper"),
            Path("/usr/bin/whisper"),
            Path.home() / "whisper.cpp" / "main",
            Path.home() / "whisper.cpp" / "main.exe",
            Path("./whisper/main"),
            Path("./whisper/main.exe")
        ]
        
        # Check if whisper is in PATH
        try:
            result = subprocess.run(["which", "whisper"], capture_output=True, text=True)
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except:
            pass
        
        # Check common locations
        for path in possible_paths:
            if path.exists() and path.is_file():
                return path
        
        # Try to find in models directory
        models_dir = self.config.get_models_path()
        whisper_dir = models_dir / "whisper.cpp"
        if whisper_dir.exists():
            for executable in ["main", "main.exe"]:
                exe_path = whisper_dir / executable
                if exe_path.exists():
                    return exe_path
        
        self.logger.warning("Whisper.cpp executable not found")
        return None
    
    async def _ensure_model_available(self):
        """Ensure Whisper model is available"""
        models_dir = self.config.get_models_path()
        whisper_models_dir = models_dir / "whisper"
        whisper_models_dir.mkdir(exist_ok=True)
        
        # Model filename mapping
        model_files = {
            "tiny": "ggml-tiny.bin",
            "base": "ggml-base.bin",
            "small": "ggml-small.bin",
            "medium": "ggml-medium.bin",
            "large": "ggml-large.bin"
        }
        
        model_file = model_files.get(self.model, "ggml-base.bin")
        model_path = whisper_models_dir / model_file
        
        if not model_path.exists():
            self.logger.info(f"Downloading Whisper model: {self.model}")
            await self._download_model(model_path)
        
        self.model_path = str(model_path)
        
        # Ensure whisper.cpp is available
        if not self.whisper_path:
            await self._install_whisper_cpp()
    
    async def _download_model(self, model_path: Path):
        """Download Whisper model"""
        model_urls = {
            "ggml-tiny.bin": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
            "ggml-base.bin": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
            "ggml-small.bin": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
            "ggml-medium.bin": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
            "ggml-large.bin": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large.bin"
        }
        
        url = model_urls.get(model_path.name)
        if not url:
            raise Exception(f"Unknown model file: {model_path.name}")
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                with open(model_path, 'wb') as f:
                    f.write(response.content)
                
                self.logger.info(f"Downloaded model to: {model_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to download model: {e}")
            raise
    
    async def _install_whisper_cpp(self):
        """Install whisper.cpp if not available"""
        models_dir = self.config.get_models_path()
        whisper_dir = models_dir / "whisper.cpp"
        
        if not whisper_dir.exists():
            self.logger.info("Installing whisper.cpp...")
            
            try:
                # Clone whisper.cpp repository
                process = await asyncio.create_subprocess_exec(
                    "git", "clone", "https://github.com/ggerganov/whisper.cpp.git", str(whisper_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode != 0:
                    raise Exception("Failed to clone whisper.cpp repository")
                
                # Build whisper.cpp
                process = await asyncio.create_subprocess_exec(
                    "make", "-C", str(whisper_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode != 0:
                    raise Exception("Failed to build whisper.cpp")
                
                # Update whisper path
                main_executable = whisper_dir / "main"
                if main_executable.exists():
                    self.whisper_path = main_executable
                    self.logger.info("whisper.cpp installed successfully")
                else:
                    raise Exception("whisper.cpp main executable not found after build")
                    
            except Exception as e:
                self.logger.error(f"Failed to install whisper.cpp: {e}")
                raise
    
    async def _process_audio(self, audio_path: str) -> str:
        """Process audio to ensure it's in the correct format for Whisper"""
        try:
            # Check if it's already a valid WAV file
            with wave.open(audio_path, 'rb') as wav_file:
                # Check format
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                framerate = wav_file.getframerate()
                
                # Whisper prefers 16kHz mono
                if channels == 1 and framerate == 16000 and sample_width == 2:
                    return audio_path
                    
        except:
            pass
        
        # Convert audio using ffmpeg if available
        try:
            output_path = audio_path.replace('.wav', '_processed.wav')
            
            process = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1", "-y", output_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                return output_path
            else:
                self.logger.warning("FFmpeg conversion failed, using original audio")
                return audio_path
                
        except Exception as e:
            self.logger.warning(f"Audio processing failed: {e}, using original")
            return audio_path
    
    async def _run_whisper(self, audio_path: str) -> str:
        """Run whisper.cpp transcription"""
        if not self.whisper_path or not self.model_path:
            raise Exception("Whisper executable or model not available")
        
        try:
            # Run whisper.cpp
            process = await asyncio.create_subprocess_exec(
                str(self.whisper_path),
                "-m", self.model_path,
                "-f", audio_path,
                "--output-txt",
                "--no-timestamps",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"Whisper transcription failed: {error_msg}")
            
            # Read transcription from output file
            output_file = Path(audio_path).with_suffix('.txt')
            if output_file.exists():
                transcription = output_file.read_text().strip()
                output_file.unlink()  # Clean up
                return transcription
            else:
                # Fallback to stdout
                return stdout.decode().strip()
                
        except Exception as e:
            self.logger.error(f"Whisper execution failed: {e}")
            raise
    
    async def transcribe_stream(self, audio_stream) -> str:
        """Transcribe streaming audio (future implementation)"""
        # This would be implemented for real-time transcription
        # For now, we'll accumulate the stream and transcribe
        audio_data = b""
        async for chunk in audio_stream:
            audio_data += chunk
        
        return await self.transcribe(audio_data)    

    async def detect_voice_activity(self, audio_data: bytes, threshold: float = 0.01) -> bool:
        """Detect if audio contains voice activity"""
        try:
            import numpy as np
            
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate RMS (Root Mean Square) energy
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            # Normalize to 0-1 range
            normalized_rms = rms / 32768.0
            
            return normalized_rms > threshold
            
        except Exception as e:
            self.logger.warning(f"Voice activity detection failed: {e}")
            return True  # Assume voice activity if detection fails
    
    async def transcribe_with_vad(self, audio_data: bytes, vad_threshold: float = 0.01) -> str:
        """Transcribe audio with voice activity detection"""
        try:
            # Check for voice activity first
            has_voice = await self.detect_voice_activity(audio_data, vad_threshold)
            
            if not has_voice:
                return ""  # No voice detected, return empty string
            
            # Proceed with transcription
            return await self.transcribe(audio_data)
            
        except Exception as e:
            self.logger.error(f"VAD transcription failed: {e}")
            return await self.transcribe(audio_data)  # Fallback to regular transcription
    
    async def start_continuous_listening(self, callback=None):
        """Start continuous listening mode"""
        self.is_listening = True
        self.logger.info("Starting continuous listening mode")
        
        while self.is_listening:
            try:
                # This would integrate with actual microphone input
                # For now, we'll just wait
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in continuous listening: {e}")
                await asyncio.sleep(1)
    
    def stop_continuous_listening(self):
        """Stop continuous listening mode"""
        self.is_listening = False
        self.logger.info("Stopped continuous listening mode")
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return [
            'auto', 'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl',
            'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 'he', 'uk', 'el',
            'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt',
            'la', 'mi', 'ml', 'cy', 'sk', 'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl',
            'kn', 'et', 'mk', 'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq',
            'sw', 'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc', 'ka',
            'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo', 'ht', 'ps', 'tk',
            'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg', 'as', 'tt', 'haw', 'ln',
            'ha', 'ba', 'jw', 'su'
        ]
    
    def set_language(self, language: str):
        """Set the transcription language"""
        supported_languages = self.get_supported_languages()
        if language in supported_languages:
            self.language = language
            self.logger.info(f"Language set to: {language}")
        else:
            self.logger.warning(f"Unsupported language: {language}")
            raise ValueError(f"Language '{language}' not supported")
    
    def _clean_transcription(self, text: str) -> str:
        """Clean up transcription text"""
        if not text:
            return ""
        
        # Remove common whisper artifacts
        text = text.strip()
        
        # Remove timestamps if any leaked through
        import re
        text = re.sub(r'\[\d+:\d+\.\d+ --> \d+:\d+\.\d+\]', '', text)
        text = re.sub(r'\(\d+:\d+\.\d+\)', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common false positives
        false_positives = [
            'Thank you for watching!',
            'Thanks for watching!',
            'Subscribe to our channel',
            'Like and subscribe',
            'you'
        ]
        
        text_lower = text.lower().strip()
        for fp in false_positives:
            if text_lower == fp.lower():
                return ""
        
        return text.strip()