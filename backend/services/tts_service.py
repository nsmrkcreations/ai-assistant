"""
Text-to-Speech Service using Piper TTS
"""

import asyncio
import logging
import tempfile
import subprocess
import os
import uuid
import platform
import tarfile
import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import aiohttp
import aiofiles

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class TTSService:
    """Text-to-Speech service using Piper TTS"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.voice = config.models.tts_voice
        self.piper_path = None
        self.voice_model_path = None
        self.audio_dir = config.get_audio_path()
        self.audio_dir.mkdir(exist_ok=True)
        
    async def start(self):
        """Start the TTS service"""
        try:
            # Install Piper if not available
            await self._ensure_piper_available()
            
            # Download voice model if not available
            await self._ensure_voice_model_available()
            
            self.logger.info(f"TTS Service started with voice: {self.voice}")
            
        except Exception as e:
            self.logger.error(f"Failed to start TTS service: {e}")
            # Don't raise - allow graceful degradation
            self.logger.warning("TTS service starting without Piper - speech synthesis will not work")
    
    async def stop(self):
        """Stop the TTS service"""
        self.logger.info("TTS Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            if self.piper_path and self.piper_path.exists() and self.voice_model_path and self.voice_model_path.exists():
                return ComponentStatus(
                    name="tts_service",
                    status=ServiceStatus.HEALTHY,
                    version=self.voice,
                    details={
                        "voice": self.voice,
                        "piper_path": str(self.piper_path),
                        "voice_model_path": str(self.voice_model_path)
                    }
                )
            else:
                return ComponentStatus(
                    name="tts_service",
                    status=ServiceStatus.DEGRADED,
                    error="Piper executable or voice model not found"
                )
                
        except Exception as e:
            return ComponentStatus(
                name="tts_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def synthesize_speech(self, text: str, output_format: str = "wav") -> str:
        """Synthesize speech from text"""
        try:
            if not self.piper_path or not self.piper_path.exists():
                raise Exception("Piper executable not found")
            
            if not self.voice_model_path or not self.voice_model_path.exists():
                raise Exception("Voice model not found")
            
            # Clean and prepare text
            clean_text = self._prepare_text_for_synthesis(text)
            if not clean_text:
                raise Exception("No valid text to synthesize")
            
            # Generate unique filename
            audio_id = str(uuid.uuid4())
            output_path = self.audio_dir / f"tts_{audio_id}.{output_format}"
            
            # Run Piper TTS
            await self._run_piper(clean_text, str(output_path))
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error synthesizing speech: {e}")
            raise Exception(f"Speech synthesis failed: {str(e)}")
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices"""
        voices = [
            {
                "id": "en_US-lessac-medium",
                "name": "Lessac (English US)",
                "language": "en-US",
                "quality": "medium",
                "gender": "female"
            },
            {
                "id": "en_US-libritts-high",
                "name": "LibriTTS (English US)",
                "language": "en-US", 
                "quality": "high",
                "gender": "neutral"
            },
            {
                "id": "en_GB-alan-medium",
                "name": "Alan (English GB)",
                "language": "en-GB",
                "quality": "medium",
                "gender": "male"
            },
            {
                "id": "en_US-amy-medium",
                "name": "Amy (English US)",
                "language": "en-US",
                "quality": "medium",
                "gender": "female"
            },
            {
                "id": "en_US-danny-low",
                "name": "Danny (English US)",
                "language": "en-US",
                "quality": "low",
                "gender": "male"
            }
        ]
        return voices
    
    async def _ensure_piper_available(self):
        """Download and install Piper if not available"""
        piper_dir = self.config.get_data_path("piper")
        piper_dir.mkdir(exist_ok=True)
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            executable_name = "piper.exe"
            if "64" in machine or "amd64" in machine:
                download_url = "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_amd64.zip"
            else:
                download_url = "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_x86.zip"
        elif system == "darwin":
            executable_name = "piper"
            if "arm" in machine or "aarch64" in machine:
                download_url = "https://github.com/rhasspy/piper/releases/latest/download/piper_macos_arm64.tar.gz"
            else:
                download_url = "https://github.com/rhasspy/piper/releases/latest/download/piper_macos_x64.tar.gz"
        else:  # Linux
            executable_name = "piper"
            if "arm" in machine or "aarch64" in machine:
                download_url = "https://github.com/rhasspy/piper/releases/latest/download/piper_linux_aarch64.tar.gz"
            else:
                download_url = "https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz"
        
        self.piper_path = piper_dir / executable_name
        
        if self.piper_path.exists():
            return
        
        try:
            self.logger.info(f"Downloading Piper TTS for {system}")
            
            # Download Piper
            if download_url.endswith('.zip'):
                archive_path = piper_dir / "piper.zip"
            else:
                archive_path = piper_dir / "piper.tar.gz"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, allow_redirects=True) as response:
                    if response.status == 200:
                        async with aiofiles.open(archive_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        # Extract archive
                        if download_url.endswith('.zip'):
                            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                                zip_ref.extractall(piper_dir)
                        else:
                            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                                tar_ref.extractall(piper_dir)
                        
                        # Find the executable
                        for file in piper_dir.rglob(executable_name):
                            if file.is_file():
                                self.piper_path = file
                                # Make executable on Unix systems
                                if system != "windows":
                                    os.chmod(file, 0o755)
                                break
                        
                        # Clean up archive
                        os.unlink(archive_path)
                        
                        if self.piper_path and self.piper_path.exists():
                            self.logger.info(f"Piper TTS downloaded: {self.piper_path}")
                        else:
                            raise Exception("Piper executable not found in downloaded package")
                    
                    else:
                        raise Exception(f"Failed to download Piper: HTTP {response.status}")
        
        except Exception as e:
            self.logger.error(f"Failed to download Piper: {e}")
            raise
    
    async def _ensure_voice_model_available(self):
        """Download voice model if not available"""
        models_dir = self.config.get_data_path("models") / "piper"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a default high-quality English voice if not specified
        if not self.voice or self.voice == "default":
            self.voice = "en_US-lessac-medium"
        
        self.voice_model_path = models_dir / f"{self.voice}.onnx"
        voice_config_path = models_dir / f"{self.voice}.onnx.json"
        
        if self.voice_model_path.exists() and voice_config_path.exists():
            return
        
        try:
            self.logger.info(f"Downloading voice model: {self.voice}")
            
            # Download voice model
            model_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{self.voice.replace('_', '/')}/{self.voice}.onnx"
            config_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{self.voice.replace('_', '/')}/{self.voice}.onnx.json"
            
            async with aiohttp.ClientSession() as session:
                # Download model file
                async with session.get(model_url, allow_redirects=True) as response:
                    if response.status == 200:
                        async with aiofiles.open(self.voice_model_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                    else:
                        raise Exception(f"Failed to download voice model: HTTP {response.status}")
                
                # Download config file
                async with session.get(config_url, allow_redirects=True) as response:
                    if response.status == 200:
                        async with aiofiles.open(voice_config_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                    else:
                        raise Exception(f"Failed to download voice config: HTTP {response.status}")
            
            self.logger.info(f"Voice model downloaded: {self.voice_model_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to download voice model: {e}")
            raise
    
    async def _run_piper(self, text: str, output_path: str):
        """Run Piper TTS to generate speech"""
        try:
            cmd = [
                str(self.piper_path),
                '--model', str(self.voice_model_path),
                '--output_file', output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send text to stdin
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=text.encode('utf-8')),
                timeout=30.0  # 30 second timeout
            )
            
            if process.returncode == 0:
                if not Path(output_path).exists():
                    raise Exception("Output file was not created")
                self.logger.debug(f"Speech synthesized: {output_path}")
            else:
                error_msg = stderr.decode('utf-8')
                raise Exception(f"Piper TTS failed: {error_msg}")
        
        except asyncio.TimeoutError:
            raise Exception("Speech synthesis timed out")
        except Exception as e:
            self.logger.error(f"Piper execution failed: {e}")
            raise
    
    async def set_voice(self, voice_id: str):
        """Change the current voice"""
        old_voice = self.voice
        self.voice = voice_id
        
        try:
            await self._ensure_voice_model_available()
            self.logger.info(f"Voice changed from {old_voice} to {voice_id}")
        except Exception as e:
            # Revert to old voice if download fails
            self.voice = old_voice
            raise Exception(f"Failed to change voice: {e}")
    
    def cleanup_old_audio_files(self, max_age_hours: int = 24):
        """Clean up old audio files"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for audio_file in self.audio_dir.glob("tts_*.wav"):
                if current_time - audio_file.stat().st_mtime > max_age_seconds:
                    audio_file.unlink()
                    self.logger.debug(f"Cleaned up old audio file: {audio_file}")
        
        except Exception as e:
            self.logger.warning(f"Failed to cleanup audio files: {e}")
        try:
            if self.piper_path and self.voice_model_path:
                return ComponentStatus(
                    name="tts_service",
                    status=ServiceStatus.HEALTHY,
                    version=self.voice,
                    details={
                        "voice": self.voice,
                        "voice_model_path": str(self.voice_model_path),
                        "piper_path": str(self.piper_path),
                        "audio_dir": str(self.audio_dir)
                    }
                )
            else:
                return ComponentStatus(
                    name="tts_service",
                    status=ServiceStatus.DEGRADED,
                    error="Piper executable or voice model not found"
                )
                
        except Exception as e:
            return ComponentStatus(
                name="tts_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def generate_speech(self, text: str, voice: Optional[str] = None) -> str:
        """Generate speech from text"""
        try:
            if not self.piper_path or not self.voice_model_path:
                raise Exception("TTS not properly initialized")
            
            # Generate unique filename
            audio_id = str(uuid.uuid4())
            audio_path = self.audio_dir / f"tts_{audio_id}.wav"
            
            # Use specified voice or default
            voice_to_use = voice or self.voice
            voice_model_path = self.voice_model_path
            
            # Run Piper TTS
            await self._run_piper(text, voice_model_path, audio_path)
            
            # Return relative path for web serving
            return f"/audio/tts_{audio_id}.wav"
            
        except Exception as e:
            self.logger.error(f"Speech generation failed: {e}")
            raise Exception(f"TTS failed: {str(e)}")
    
    async def _ensure_piper_available(self):
        """Ensure Piper TTS is available"""
        # Try to find existing Piper installation
        self.piper_path = self._find_piper_executable()
        
        if not self.piper_path:
            # Install Piper
            await self._install_piper()
    
    def _find_piper_executable(self) -> Optional[Path]:
        """Find Piper executable"""
        possible_paths = [
            Path("piper/piper"),
            Path("piper/piper.exe"),
            Path("/usr/local/bin/piper"),
            Path("/usr/bin/piper"),
            Path.home() / "piper" / "piper",
            Path.home() / "piper" / "piper.exe"
        ]
        
        # Check if piper is in PATH
        try:
            result = subprocess.run(["which", "piper"], capture_output=True, text=True)
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except:
            pass
        
        # Check common locations
        for path in possible_paths:
            if path.exists() and path.is_file():
                return path
        
        # Check in models directory
        models_dir = self.config.get_models_path()
        piper_dir = models_dir / "piper"
        if piper_dir.exists():
            for executable in ["piper", "piper.exe"]:
                exe_path = piper_dir / executable
                if exe_path.exists():
                    return exe_path
        
        return None
    
    async def _install_piper(self):
        """Install Piper TTS"""
        models_dir = self.config.get_models_path()
        piper_dir = models_dir / "piper"
        piper_dir.mkdir(exist_ok=True)
        
        try:
            import platform
            system = platform.system().lower()
            arch = platform.machine().lower()
            
            # Determine download URL based on platform
            if system == "windows":
                if "64" in arch:
                    url = "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_amd64.zip"
                else:
                    url = "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_x86.zip"
            elif system == "darwin":
                url = "https://github.com/rhasspy/piper/releases/latest/download/piper_macos_x64.tar.gz"
            else:  # Linux
                if "64" in arch:
                    url = "https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz"
                else:
                    url = "https://github.com/rhasspy/piper/releases/latest/download/piper_linux_armv7.tar.gz"
            
            # Download and extract
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(response.content)
                    temp_path = temp_file.name
                
                # Extract
                if url.endswith('.zip'):
                    import zipfile
                    with zipfile.ZipFile(temp_path, 'r') as zip_file:
                        zip_file.extractall(piper_dir)
                else:
                    import tarfile
                    with tarfile.open(temp_path, 'r:gz') as tar_file:
                        tar_file.extractall(piper_dir)
                
                # Find executable
                for item in piper_dir.rglob("piper*"):
                    if item.is_file() and os.access(item, os.X_OK):
                        self.piper_path = item
                        break
                
                # Cleanup
                os.unlink(temp_path)
                
                if self.piper_path:
                    self.logger.info(f"Piper installed at: {self.piper_path}")
                else:
                    raise Exception("Piper executable not found after installation")
                    
        except Exception as e:
            self.logger.error(f"Piper installation failed: {e}")
            raise
    
    async def _ensure_voice_model_available(self):
        """Ensure voice model is available"""
        models_dir = self.config.get_models_path()
        voice_models_dir = models_dir / "piper_voices"
        voice_models_dir.mkdir(exist_ok=True)
        
        # Voice model mapping
        voice_files = {
            "en_US-lessac-medium": {
                "model": "en_US-lessac-medium.onnx",
                "config": "en_US-lessac-medium.onnx.json",
                "url_base": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/"
            },
            "en_US-amy-medium": {
                "model": "en_US-amy-medium.onnx",
                "config": "en_US-amy-medium.onnx.json",
                "url_base": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/"
            }
        }
        
        voice_info = voice_files.get(self.voice)
        if not voice_info:
            # Default to lessac
            voice_info = voice_files["en_US-lessac-medium"]
            self.voice = "en_US-lessac-medium"
        
        model_path = voice_models_dir / voice_info["model"]
        config_path = voice_models_dir / voice_info["config"]
        
        # Download model if not exists
        if not model_path.exists():
            await self._download_voice_model(voice_info["url_base"] + voice_info["model"], model_path)
        
        # Download config if not exists
        if not config_path.exists():
            await self._download_voice_model(voice_info["url_base"] + voice_info["config"], config_path)
        
        self.voice_model_path = str(model_path)
    
    async def _download_voice_model(self, url: str, output_path: Path):
        """Download voice model"""
        try:
            self.logger.info(f"Downloading voice model: {url}")
            
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                self.logger.info(f"Downloaded voice model to: {output_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to download voice model: {e}")
            raise
    
    async def _run_piper(self, text: str, model_path: str, output_path: Path):
        """Run Piper TTS"""
        if not self.piper_path:
            raise Exception("Piper executable not available")
        
        try:
            # Prepare command
            cmd = [
                str(self.piper_path),
                "--model", model_path,
                "--output_file", str(output_path)
            ]
            
            # Run Piper
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"Piper TTS failed: {error_msg}")
            
            if not output_path.exists():
                raise Exception("TTS output file not created")
                
        except Exception as e:
            self.logger.error(f"Piper execution failed: {e}")
            raise
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices"""
        return [
            {
                "id": "en_US-lessac-medium",
                "name": "Lessac (US English, Medium)",
                "language": "en-US",
                "gender": "female"
            },
            {
                "id": "en_US-amy-medium", 
                "name": "Amy (US English, Medium)",
                "language": "en-US",
                "gender": "female"
            }
        ]
    
    async def set_voice(self, voice_id: str):
        """Set active voice"""
        available_voices = await self.list_voices()
        voice_ids = [v["id"] for v in available_voices]
        
        if voice_id in voice_ids:
            self.voice = voice_id
            # Re-initialize voice model
            await self._ensure_voice_model_available()
        else:
            raise ValueError(f"Voice {voice_id} not available")
    
    async def generate_speech_stream(self, text: str) -> bytes:
        """Generate speech and return audio data directly"""
        try:
            # Generate to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            await self._run_piper(text, self.voice_model_path, temp_path)
            
            # Read audio data
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # Cleanup
            temp_path.unlink()
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Speech stream generation failed: {e}")
            raise
   
   async def synthesize_speech_stream(self, text: str) -> bytes:
        """Synthesize speech and return audio data as bytes"""
        try:
            # Generate to temporary file first
            temp_path = await self.synthesize_speech(text)
            
            # Read audio data
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Stream synthesis failed: {e}")
            raise
    
    async def synthesize_ssml(self, ssml_text: str, output_format: str = "wav") -> str:
        """Synthesize speech from SSML text"""
        try:
            # Parse SSML and convert to plain text with prosody hints
            plain_text = self._parse_ssml(ssml_text)
            
            # Use regular synthesis for now (Piper doesn't support SSML directly)
            return await self.synthesize_speech(plain_text, output_format)
            
        except Exception as e:
            self.logger.error(f"SSML synthesis failed: {e}")
            raise
    
    def _parse_ssml(self, ssml_text: str) -> str:
        """Parse SSML and extract plain text with prosody hints"""
        try:
            import re
            
            # Remove SSML tags but keep the text content
            # This is a simple parser - a full implementation would handle prosody
            text = re.sub(r'<[^>]+>', '', ssml_text)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            self.logger.warning(f"SSML parsing failed: {e}")
            return ssml_text  # Return original if parsing fails
    
    async def set_voice_parameters(self, voice_id: str, speed: float = 1.0, pitch: float = 1.0):
        """Set voice parameters (speed, pitch)"""
        try:
            # Store parameters for future synthesis
            self.voice_parameters = {
                'voice_id': voice_id,
                'speed': max(0.1, min(3.0, speed)),  # Clamp between 0.1 and 3.0
                'pitch': max(0.5, min(2.0, pitch))   # Clamp between 0.5 and 2.0
            }
            
            # Update current voice if different
            if voice_id != self.voice:
                await self.set_voice(voice_id)
            
            self.logger.info(f"Voice parameters set: {self.voice_parameters}")
            
        except Exception as e:
            self.logger.error(f"Failed to set voice parameters: {e}")
            raise
    
    async def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific voice"""
        voices = await self.get_available_voices()
        
        for voice in voices:
            if voice['id'] == voice_id:
                # Add additional info
                voice_info = voice.copy()
                voice_info['available'] = await self._is_voice_available(voice_id)
                voice_info['model_size'] = await self._get_voice_model_size(voice_id)
                return voice_info
        
        return None
    
    async def _is_voice_available(self, voice_id: str) -> bool:
        """Check if a voice model is available locally"""
        try:
            models_dir = self.config.get_data_path("models") / "piper"
            model_path = models_dir / f"{voice_id}.onnx"
            config_path = models_dir / f"{voice_id}.onnx.json"
            
            return model_path.exists() and config_path.exists()
            
        except Exception:
            return False
    
    async def _get_voice_model_size(self, voice_id: str) -> Optional[int]:
        """Get the size of a voice model in bytes"""
        try:
            models_dir = self.config.get_data_path("models") / "piper"
            model_path = models_dir / f"{voice_id}.onnx"
            
            if model_path.exists():
                return model_path.stat().st_size
            
            return None
            
        except Exception:
            return None
    
    async def preload_voice(self, voice_id: str):
        """Preload a voice model for faster synthesis"""
        try:
            # Download voice model if not available
            old_voice = self.voice
            self.voice = voice_id
            
            await self._ensure_voice_model_available()
            
            # Restore original voice
            self.voice = old_voice
            
            self.logger.info(f"Voice {voice_id} preloaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to preload voice {voice_id}: {e}")
            raise
    
    def get_synthesis_stats(self) -> Dict[str, Any]:
        """Get synthesis statistics"""
        return {
            'current_voice': self.voice,
            'audio_files_generated': len(list(self.audio_dir.glob('tts_*.wav'))),
            'piper_available': self.piper_path is not None and self.piper_path.exists(),
            'voice_model_available': self.voice_model_path is not None and self.voice_model_path.exists(),
            'audio_directory': str(self.audio_dir)
        }
    
    async def cleanup_old_audio_files(self, max_age_hours: int = 24):
        """Clean up old generated audio files"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            
            for audio_file in self.audio_dir.glob("tts_*.wav"):
                if current_time - audio_file.stat().st_mtime > max_age_seconds:
                    audio_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} old audio files")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup audio files: {e}")
            return 0