"""
Creative Automation Service for video, animation, and multimedia content creation
"""

import asyncio
import logging
import subprocess
import time
import uuid
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import json
import tempfile
import shutil
import os

# FFmpeg and multimedia imports
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

# Image processing imports
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class CreativeAutomationService:
    """Service for creative content automation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_projects: Dict[str, Dict] = {}
        self.templates_dir = config.get_data_path("templates")
        self.output_dir = config.get_data_path("creative_output")
        self.temp_dir = config.get_temp_path()
        
        # Create directories
        self.templates_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
    async def start(self):
        """Start the creative automation service"""
        try:
            # Check dependencies
            await self._check_dependencies()
            
            # Initialize templates
            await self._initialize_templates()
            
            self.logger.info("Creative Automation Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start creative automation service: {e}")
            raise
    
    async def stop(self):
        """Stop the creative automation service"""
        # Cancel any active projects
        for project_id in list(self.active_projects.keys()):
            await self.cancel_project(project_id)
        
        self.logger.info("Creative Automation Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="creative_automation_service",
                status=ServiceStatus.HEALTHY if (FFMPEG_AVAILABLE and PIL_AVAILABLE) else ServiceStatus.DEGRADED,
                details={
                    "ffmpeg_available": FFMPEG_AVAILABLE,
                    "pil_available": PIL_AVAILABLE,
                    "active_projects": len(self.active_projects),
                    "templates_count": len(list(self.templates_dir.glob("*.json"))),
                    "output_dir": str(self.output_dir)
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="creative_automation_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def create_video_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new video project"""
        try:
            project_id = str(uuid.uuid4())
            
            project = {
                'id': project_id,
                'type': 'video',
                'title': project_data.get('title', 'Untitled Video'),
                'description': project_data.get('description', ''),
                'created_at': time.time(),
                'status': 'created',
                'settings': {
                    'resolution': project_data.get('resolution', '1920x1080'),
                    'fps': project_data.get('fps', 30),
                    'duration': project_data.get('duration', 10),
                    'format': project_data.get('format', 'mp4')
                },
                'assets': [],
                'timeline': [],
                'output_path': None
            }
            
            self.active_projects[project_id] = project
            
            return {
                'success': True,
                'project_id': project_id,
                'project': project
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_animation_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new animation project"""
        try:
            project_id = str(uuid.uuid4())
            
            project = {
                'id': project_id,
                'type': 'animation',
                'title': project_data.get('title', 'Untitled Animation'),
                'description': project_data.get('description', ''),
                'created_at': time.time(),
                'status': 'created',
                'settings': {
                    'resolution': project_data.get('resolution', '1920x1080'),
                    'fps': project_data.get('fps', 24),
                    'duration': project_data.get('duration', 5),
                    'style': project_data.get('style', 'modern'),
                    'format': project_data.get('format', 'mp4')
                },
                'scenes': [],
                'characters': [],
                'assets': [],
                'output_path': None
            }
            
            self.active_projects[project_id] = project
            
            return {
                'success': True,
                'project_id': project_id,
                'project': project
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def add_video_asset(self, project_id: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add an asset to a video project"""
        try:
            if project_id not in self.active_projects:
                return {'success': False, 'error': 'Project not found'}
            
            project = self.active_projects[project_id]
            
            asset = {
                'id': str(uuid.uuid4()),
                'type': asset_data.get('type', 'image'),
                'path': asset_data.get('path'),
                'duration': asset_data.get('duration', 3),
                'start_time': asset_data.get('start_time', 0),
                'effects': asset_data.get('effects', []),
                'properties': asset_data.get('properties', {})
            }
            
            project['assets'].append(asset)
            
            return {
                'success': True,
                'asset_id': asset['id'],
                'asset': asset
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def generate_slideshow(self, project_id: str, images: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a slideshow from images"""
        try:
            if not FFMPEG_AVAILABLE:
                return {'success': False, 'error': 'FFmpeg not available'}
            
            if project_id not in self.active_projects:
                return {'success': False, 'error': 'Project not found'}
            
            project = self.active_projects[project_id]
            project['status'] = 'processing'
            
            # Settings
            duration_per_image = settings.get('duration_per_image', 3)
            transition_duration = settings.get('transition_duration', 0.5)
            resolution = settings.get('resolution', '1920x1080')
            fps = settings.get('fps', 30)
            
            # Create output filename
            output_filename = f"slideshow_{project_id}_{int(time.time())}.mp4"
            output_path = self.output_dir / output_filename
            
            # Create FFmpeg filter complex for slideshow
            filter_complex = await self._create_slideshow_filter(
                images, duration_per_image, transition_duration, resolution, fps
            )
            
            # Build FFmpeg command
            cmd = ['ffmpeg', '-y']
            
            # Add input images
            for image_path in images:
                cmd.extend(['-loop', '1', '-t', str(duration_per_image), '-i', image_path])
            
            # Add filter complex
            cmd.extend(['-filter_complex', filter_complex])
            
            # Output settings
            cmd.extend([
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', str(fps),
                str(output_path)
            ])
            
            # Execute FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                project['status'] = 'completed'
                project['output_path'] = str(output_path)
                
                return {
                    'success': True,
                    'output_path': str(output_path),
                    'duration': len(images) * duration_per_image,
                    'file_size': output_path.stat().st_size
                }
            else:
                project['status'] = 'failed'
                error_msg = stderr.decode('utf-8')
                return {'success': False, 'error': f'FFmpeg error: {error_msg}'}
            
        except Exception as e:
            if project_id in self.active_projects:
                self.active_projects[project_id]['status'] = 'failed'
            return {'success': False, 'error': str(e)}
    
    async def create_text_animation(self, project_id: str, text_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create animated text"""
        try:
            if not PIL_AVAILABLE:
                return {'success': False, 'error': 'PIL not available'}
            
            if project_id not in self.active_projects:
                return {'success': False, 'error': 'Project not found'}
            
            project = self.active_projects[project_id]
            project['status'] = 'processing'
            
            # Text settings
            text = text_data.get('text', 'Sample Text')
            font_size = text_data.get('font_size', 72)
            font_color = text_data.get('font_color', '#FFFFFF')
            background_color = text_data.get('background_color', '#000000')
            animation_type = text_data.get('animation_type', 'fade_in')
            duration = text_data.get('duration', 3)
            fps = text_data.get('fps', 30)
            resolution = text_data.get('resolution', '1920x1080')
            
            # Parse resolution
            width, height = map(int, resolution.split('x'))
            
            # Create frames
            frames = []
            total_frames = int(duration * fps)
            
            for frame_num in range(total_frames):
                # Create frame
                img = Image.new('RGB', (width, height), background_color)
                draw = ImageDraw.Draw(img)
                
                # Calculate animation progress
                progress = frame_num / total_frames
                
                # Apply animation
                if animation_type == 'fade_in':
                    alpha = int(255 * progress)
                    text_color = self._adjust_color_alpha(font_color, alpha)
                elif animation_type == 'slide_in':
                    x_offset = int(width * (1 - progress))
                    text_color = font_color
                else:
                    text_color = font_color
                    x_offset = 0
                
                # Draw text
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # Get text size
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Center text
                x = (width - text_width) // 2
                y = (height - text_height) // 2
                
                if animation_type == 'slide_in':
                    x += x_offset
                
                draw.text((x, y), text, fill=text_color, font=font)
                
                # Save frame
                frame_path = self.temp_dir / f"frame_{project_id}_{frame_num:06d}.png"
                img.save(frame_path)
                frames.append(str(frame_path))
            
            # Convert frames to video
            output_filename = f"text_animation_{project_id}_{int(time.time())}.mp4"
            output_path = self.output_dir / output_filename
            
            # Create video from frames
            result = await self._frames_to_video(frames, output_path, fps)
            
            # Cleanup frames
            for frame_path in frames:
                try:
                    os.unlink(frame_path)
                except:
                    pass
            
            if result['success']:
                project['status'] = 'completed'
                project['output_path'] = str(output_path)
                
                return {
                    'success': True,
                    'output_path': str(output_path),
                    'duration': duration,
                    'frames': total_frames,
                    'file_size': output_path.stat().st_size
                }
            else:
                project['status'] = 'failed'
                return result
            
        except Exception as e:
            if project_id in self.active_projects:
                self.active_projects[project_id]['status'] = 'failed'
            return {'success': False, 'error': str(e)}
    
    async def create_logo_animation(self, project_id: str, logo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create animated logo"""
        try:
            if project_id not in self.active_projects:
                return {'success': False, 'error': 'Project not found'}
            
            project = self.active_projects[project_id]
            project['status'] = 'processing'
            
            # Logo settings
            logo_path = logo_data.get('logo_path')
            animation_type = logo_data.get('animation_type', 'zoom_in')
            duration = logo_data.get('duration', 3)
            background_color = logo_data.get('background_color', '#FFFFFF')
            
            if not logo_path or not Path(logo_path).exists():
                return {'success': False, 'error': 'Logo file not found'}
            
            # Create logo animation using FFmpeg
            output_filename = f"logo_animation_{project_id}_{int(time.time())}.mp4"
            output_path = self.output_dir / output_filename
            
            # Build FFmpeg command based on animation type
            if animation_type == 'zoom_in':
                filter_complex = f"[0:v]scale=iw*min(1920/iw\\,1080/ih):ih*min(1920/iw\\,1080/ih),pad=1920:1080:(1920-iw)/2:(1080-ih)/2:color={background_color},zoompan=z='min(zoom+0.0015,1.5)':d={duration*30}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080[v]"
            elif animation_type == 'fade_in':
                filter_complex = f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(1920-iw)/2:(1080-ih)/2:color={background_color},fade=t=in:st=0:d=1[v]"
            else:
                filter_complex = f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(1920-iw)/2:(1080-ih)/2:color={background_color}[v]"
            
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-i', logo_path,
                '-filter_complex', filter_complex,
                '-map', '[v]',
                '-t', str(duration),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', '30',
                str(output_path)
            ]
            
            # Execute FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                project['status'] = 'completed'
                project['output_path'] = str(output_path)
                
                return {
                    'success': True,
                    'output_path': str(output_path),
                    'duration': duration,
                    'animation_type': animation_type,
                    'file_size': output_path.stat().st_size
                }
            else:
                project['status'] = 'failed'
                error_msg = stderr.decode('utf-8')
                return {'success': False, 'error': f'FFmpeg error: {error_msg}'}
            
        except Exception as e:
            if project_id in self.active_projects:
                self.active_projects[project_id]['status'] = 'failed'
            return {'success': False, 'error': str(e)}
    
    async def create_presentation_video(self, project_id: str, presentation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a presentation video from slides"""
        try:
            if project_id not in self.active_projects:
                return {'success': False, 'error': 'Project not found'}
            
            project = self.active_projects[project_id]
            project['status'] = 'processing'
            
            slides = presentation_data.get('slides', [])
            if not slides:
                return {'success': False, 'error': 'No slides provided'}
            
            # Settings
            slide_duration = presentation_data.get('slide_duration', 5)
            transition_duration = presentation_data.get('transition_duration', 0.5)
            resolution = presentation_data.get('resolution', '1920x1080')
            background_music = presentation_data.get('background_music')
            
            # Generate slide images
            slide_images = []
            for i, slide in enumerate(slides):
                slide_image = await self._create_slide_image(slide, resolution, i)
                if slide_image:
                    slide_images.append(slide_image)
            
            if not slide_images:
                return {'success': False, 'error': 'Failed to create slide images'}
            
            # Create slideshow
            slideshow_result = await self.generate_slideshow(
                project_id, 
                slide_images, 
                {
                    'duration_per_image': slide_duration,
                    'transition_duration': transition_duration,
                    'resolution': resolution
                }
            )
            
            if not slideshow_result['success']:
                return slideshow_result
            
            # Add background music if provided
            if background_music and Path(background_music).exists():
                final_output = await self._add_background_music(
                    slideshow_result['output_path'],
                    background_music,
                    project_id
                )
                
                if final_output['success']:
                    # Replace original with music version
                    os.unlink(slideshow_result['output_path'])
                    slideshow_result['output_path'] = final_output['output_path']
                    project['output_path'] = final_output['output_path']
            
            # Cleanup slide images
            for slide_image in slide_images:
                try:
                    os.unlink(slide_image)
                except:
                    pass
            
            return slideshow_result
            
        except Exception as e:
            if project_id in self.active_projects:
                self.active_projects[project_id]['status'] = 'failed'
            return {'success': False, 'error': str(e)}
    
    async def _create_slide_image(self, slide_data: Dict[str, Any], resolution: str, slide_num: int) -> Optional[str]:
        """Create an image from slide data"""
        try:
            if not PIL_AVAILABLE:
                return None
            
            width, height = map(int, resolution.split('x'))
            
            # Create slide image
            img = Image.new('RGB', (width, height), slide_data.get('background_color', '#FFFFFF'))
            draw = ImageDraw.Draw(img)
            
            # Add title
            title = slide_data.get('title', '')
            if title:
                try:
                    title_font = ImageFont.truetype("arial.ttf", 72)
                except:
                    title_font = ImageFont.load_default()
                
                # Center title
                bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = bbox[2] - bbox[0]
                title_x = (width - title_width) // 2
                title_y = height // 6
                
                draw.text((title_x, title_y), title, fill='#000000', font=title_font)
            
            # Add content
            content = slide_data.get('content', '')
            if content:
                try:
                    content_font = ImageFont.truetype("arial.ttf", 36)
                except:
                    content_font = ImageFont.load_default()
                
                # Wrap text
                lines = self._wrap_text(content, content_font, width - 200)
                
                y_offset = height // 3
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=content_font)
                    line_width = bbox[2] - bbox[0]
                    line_x = (width - line_width) // 2
                    
                    draw.text((line_x, y_offset), line, fill='#333333', font=content_font)
                    y_offset += 50
            
            # Save slide image
            slide_path = self.temp_dir / f"slide_{slide_num}_{int(time.time())}.png"
            img.save(slide_path)
            
            return str(slide_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create slide image: {e}")
            return None
    
    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """Wrap text to fit within max width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            # Simple width estimation (not perfect but works)
            if len(test_line) * 20 <= max_width:  # Rough character width estimation
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _adjust_color_alpha(self, color: str, alpha: int) -> str:
        """Adjust color alpha for fade effects"""
        if color.startswith('#'):
            # Convert hex to RGB with alpha
            hex_color = color[1:]
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"rgba({r},{g},{b},{alpha/255:.2f})"
        return color
    
    async def _create_slideshow_filter(self, images: List[str], duration: float, transition: float, resolution: str, fps: int) -> str:
        """Create FFmpeg filter complex for slideshow"""
        # Simple slideshow filter - can be enhanced with more complex transitions
        filter_parts = []
        
        for i, image_path in enumerate(images):
            filter_parts.append(f"[{i}:v]scale={resolution}:force_original_aspect_ratio=decrease,pad={resolution}:(ow-iw)/2:(oh-ih)/2[img{i}]")
        
        # Concatenate images
        concat_inputs = ''.join([f"[img{i}]" for i in range(len(images))])
        filter_parts.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[out]")
        
        return ';'.join(filter_parts)
    
    async def _frames_to_video(self, frames: List[str], output_path: Path, fps: int) -> Dict[str, Any]:
        """Convert frame images to video"""
        try:
            if not FFMPEG_AVAILABLE:
                return {'success': False, 'error': 'FFmpeg not available'}
            
            # Create pattern for FFmpeg
            frame_pattern = str(self.temp_dir / f"frame_{frames[0].split('_')[1]}_*.png")
            
            cmd = [
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-pattern_type', 'glob',
                '-i', frame_pattern,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', str(fps),
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {'success': True, 'output_path': str(output_path)}
            else:
                error_msg = stderr.decode('utf-8')
                return {'success': False, 'error': f'FFmpeg error: {error_msg}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _add_background_music(self, video_path: str, music_path: str, project_id: str) -> Dict[str, Any]:
        """Add background music to video"""
        try:
            if not FFMPEG_AVAILABLE:
                return {'success': False, 'error': 'FFmpeg not available'}
            
            output_filename = f"video_with_music_{project_id}_{int(time.time())}.mp4"
            output_path = self.output_dir / output_filename
            
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', music_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {'success': True, 'output_path': str(output_path)}
            else:
                error_msg = stderr.decode('utf-8')
                return {'success': False, 'error': f'FFmpeg error: {error_msg}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_dependencies(self):
        """Check if required dependencies are available"""
        # Check FFmpeg
        try:
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                global FFMPEG_AVAILABLE
                FFMPEG_AVAILABLE = True
                self.logger.info("FFmpeg is available")
            else:
                self.logger.warning("FFmpeg not found")
        except:
            self.logger.warning("FFmpeg not available")
        
        # Check PIL
        if not PIL_AVAILABLE:
            try:
                import subprocess
                import sys
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow'])
                
                global PIL_AVAILABLE
                from PIL import Image, ImageDraw, ImageFont
                PIL_AVAILABLE = True
                self.logger.info("PIL installed and available")
            except:
                self.logger.warning("Failed to install PIL")
    
    async def _initialize_templates(self):
        """Initialize creative templates"""
        try:
            # Create default templates
            templates = {
                'simple_slideshow': {
                    'name': 'Simple Slideshow',
                    'description': 'Basic slideshow with fade transitions',
                    'settings': {
                        'duration_per_slide': 3,
                        'transition_duration': 0.5,
                        'resolution': '1920x1080'
                    }
                },
                'text_animation': {
                    'name': 'Text Animation',
                    'description': 'Animated text with various effects',
                    'settings': {
                        'font_size': 72,
                        'animation_type': 'fade_in',
                        'duration': 3
                    }
                },
                'logo_reveal': {
                    'name': 'Logo Reveal',
                    'description': 'Animated logo reveal',
                    'settings': {
                        'animation_type': 'zoom_in',
                        'duration': 3,
                        'background_color': '#FFFFFF'
                    }
                }
            }
            
            for template_name, template_data in templates.items():
                template_path = self.templates_dir / f"{template_name}.json"
                if not template_path.exists():
                    with open(template_path, 'w') as f:
                        json.dump(template_data, f, indent=2)
            
            self.logger.info(f"Initialized {len(templates)} creative templates")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize templates: {e}")
    
    async def cancel_project(self, project_id: str) -> bool:
        """Cancel an active project"""
        if project_id in self.active_projects:
            self.active_projects[project_id]['status'] = 'cancelled'
            # Cleanup any temporary files
            await self._cleanup_project_files(project_id)
            return True
        return False
    
    async def _cleanup_project_files(self, project_id: str):
        """Clean up temporary files for a project"""
        try:
            # Remove temporary files
            for temp_file in self.temp_dir.glob(f"*{project_id}*"):
                try:
                    temp_file.unlink()
                except:
                    pass
        except Exception as e:
            self.logger.warning(f"Failed to cleanup project files: {e}")
    
    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a project"""
        return self.active_projects.get(project_id)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all active projects"""
        return list(self.active_projects.values())
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available templates"""
        templates = []
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    template_data['id'] = template_file.stem
                    templates.append(template_data)
            except:
                pass
        return templates
    
    def get_creative_stats(self) -> Dict[str, Any]:
        """Get creative automation statistics"""
        return {
            "ffmpeg_available": FFMPEG_AVAILABLE,
            "pil_available": PIL_AVAILABLE,
            "active_projects": len(self.active_projects),
            "completed_projects": len([p for p in self.active_projects.values() if p['status'] == 'completed']),
            "templates_count": len(list(self.templates_dir.glob("*.json"))),
            "output_files": len(list(self.output_dir.glob("*"))),
            "temp_files": len(list(self.temp_dir.glob("*")))
        }