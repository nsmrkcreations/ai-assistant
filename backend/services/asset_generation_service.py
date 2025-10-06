"""
Asset Generation Service for AI-powered image, video, and content creation
"""

import asyncio
import logging
import time
import uuid
import base64
import io
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import json
import tempfile
import hashlib

# Image processing imports
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Stable Diffusion imports
try:
    import torch
    from diffusers import StableDiffusionPipeline, StableDiffusionImg2ImgPipeline, DiffusionPipeline
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False

# Additional AI model imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class AssetGenerationService:
    """Service for AI-powered asset generation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.models_dir = config.get_data_path("ai_models")
        self.output_dir = config.get_data_path("generated_assets")
        self.cache_dir = config.get_data_path("generation_cache")
        
        # Create directories
        self.models_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Model instances
        self.sd_pipeline = None
        self.img2img_pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu" if DIFFUSERS_AVAILABLE else None
        
        # Generation queue
        self.generation_queue: Dict[str, Dict] = {}
        self.active_generations: Dict[str, Dict] = {}
        
    async def start(self):
        """Start the asset generation service"""
        try:
            # Check dependencies
            await self._check_dependencies()
            
            # Initialize models
            if DIFFUSERS_AVAILABLE:
                await self._initialize_models()
            
            self.logger.info("Asset Generation Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start asset generation service: {e}")
            # Don't raise - allow service to start in degraded mode
    
    async def stop(self):
        """Stop the asset generation service"""
        # Cancel any active generations
        for gen_id in list(self.active_generations.keys()):
            await self.cancel_generation(gen_id)
        
        # Clear models from memory
        if self.sd_pipeline:
            del self.sd_pipeline
            self.sd_pipeline = None
        
        if self.img2img_pipeline:
            del self.img2img_pipeline
            self.img2img_pipeline = None
        
        # Clear GPU cache if available
        if DIFFUSERS_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.logger.info("Asset Generation Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="asset_generation_service",
                status=ServiceStatus.HEALTHY if DIFFUSERS_AVAILABLE else ServiceStatus.DEGRADED,
                details={
                    "diffusers_available": DIFFUSERS_AVAILABLE,
                    "pil_available": PIL_AVAILABLE,
                    "device": self.device,
                    "models_loaded": self.sd_pipeline is not None,
                    "active_generations": len(self.active_generations),
                    "queued_generations": len(self.generation_queue),
                    "cuda_available": torch.cuda.is_available() if DIFFUSERS_AVAILABLE else False
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="asset_generation_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def generate_image(self, generation_request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an image using AI"""
        try:
            generation_id = str(uuid.uuid4())
            
            # Validate request
            prompt = generation_request.get('prompt')
            if not prompt:
                return {'success': False, 'error': 'Prompt is required'}
            
            # Generation parameters
            params = {
                'prompt': prompt,
                'negative_prompt': generation_request.get('negative_prompt', ''),
                'width': generation_request.get('width', 512),
                'height': generation_request.get('height', 512),
                'num_inference_steps': generation_request.get('steps', 20),
                'guidance_scale': generation_request.get('guidance_scale', 7.5),
                'num_images': generation_request.get('num_images', 1),
                'seed': generation_request.get('seed'),
                'style': generation_request.get('style', 'realistic'),
                'quality': generation_request.get('quality', 'standard')
            }
            
            # Check cache first
            cache_key = self._generate_cache_key(params)
            cached_result = await self._check_cache(cache_key)
            if cached_result:
                return {
                    'success': True,
                    'generation_id': generation_id,
                    'images': cached_result['images'],
                    'cached': True,
                    'parameters': params
                }
            
            # Add to generation queue
            generation_task = {
                'id': generation_id,
                'type': 'text_to_image',
                'parameters': params,
                'status': 'queued',
                'created_at': time.time(),
                'cache_key': cache_key
            }
            
            self.generation_queue[generation_id] = generation_task
            
            # Start generation
            asyncio.create_task(self._process_generation(generation_id))
            
            return {
                'success': True,
                'generation_id': generation_id,
                'status': 'queued',
                'estimated_time': self._estimate_generation_time(params)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def generate_image_from_image(self, generation_request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an image from an existing image (img2img)"""
        try:
            generation_id = str(uuid.uuid4())
            
            # Validate request
            prompt = generation_request.get('prompt')
            source_image_path = generation_request.get('source_image')
            
            if not prompt:
                return {'success': False, 'error': 'Prompt is required'}
            
            if not source_image_path or not Path(source_image_path).exists():
                return {'success': False, 'error': 'Source image is required and must exist'}
            
            # Generation parameters
            params = {
                'prompt': prompt,
                'source_image': source_image_path,
                'negative_prompt': generation_request.get('negative_prompt', ''),
                'strength': generation_request.get('strength', 0.75),
                'num_inference_steps': generation_request.get('steps', 20),
                'guidance_scale': generation_request.get('guidance_scale', 7.5),
                'num_images': generation_request.get('num_images', 1),
                'seed': generation_request.get('seed')
            }
            
            # Add to generation queue
            generation_task = {
                'id': generation_id,
                'type': 'image_to_image',
                'parameters': params,
                'status': 'queued',
                'created_at': time.time()
            }
            
            self.generation_queue[generation_id] = generation_task
            
            # Start generation
            asyncio.create_task(self._process_generation(generation_id))
            
            return {
                'success': True,
                'generation_id': generation_id,
                'status': 'queued',
                'estimated_time': self._estimate_generation_time(params)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def upscale_image(self, upscale_request: Dict[str, Any]) -> Dict[str, Any]:
        """Upscale an image using AI"""
        try:
            generation_id = str(uuid.uuid4())
            
            source_image_path = upscale_request.get('source_image')
            if not source_image_path or not Path(source_image_path).exists():
                return {'success': False, 'error': 'Source image is required and must exist'}
            
            scale_factor = upscale_request.get('scale_factor', 2)
            method = upscale_request.get('method', 'lanczos')
            
            # Add to generation queue
            generation_task = {
                'id': generation_id,
                'type': 'upscale',
                'parameters': {
                    'source_image': source_image_path,
                    'scale_factor': scale_factor,
                    'method': method
                },
                'status': 'queued',
                'created_at': time.time()
            }
            
            self.generation_queue[generation_id] = generation_task
            
            # Start generation
            asyncio.create_task(self._process_generation(generation_id))
            
            return {
                'success': True,
                'generation_id': generation_id,
                'status': 'queued'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_thumbnail(self, thumbnail_request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a thumbnail from an image"""
        try:
            if not PIL_AVAILABLE:
                return {'success': False, 'error': 'PIL not available'}
            
            source_image_path = thumbnail_request.get('source_image')
            if not source_image_path or not Path(source_image_path).exists():
                return {'success': False, 'error': 'Source image is required and must exist'}
            
            size = thumbnail_request.get('size', (256, 256))
            quality = thumbnail_request.get('quality', 85)
            
            # Load and resize image
            with Image.open(source_image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumbnail_filename = f"thumbnail_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
                thumbnail_path = self.output_dir / thumbnail_filename
                
                img.save(thumbnail_path, 'JPEG', quality=quality, optimize=True)
            
            return {
                'success': True,
                'thumbnail_path': str(thumbnail_path),
                'size': size,
                'file_size': thumbnail_path.stat().st_size
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def apply_image_filters(self, filter_request: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to an image"""
        try:
            if not PIL_AVAILABLE:
                return {'success': False, 'error': 'PIL not available'}
            
            source_image_path = filter_request.get('source_image')
            if not source_image_path or not Path(source_image_path).exists():
                return {'success': False, 'error': 'Source image is required and must exist'}
            
            filters = filter_request.get('filters', [])
            
            # Load image
            with Image.open(source_image_path) as img:
                # Apply filters
                for filter_config in filters:
                    filter_type = filter_config.get('type')
                    
                    if filter_type == 'blur':
                        radius = filter_config.get('radius', 2)
                        img = img.filter(ImageFilter.GaussianBlur(radius=radius))
                    
                    elif filter_type == 'sharpen':
                        img = img.filter(ImageFilter.SHARPEN)
                    
                    elif filter_type == 'brightness':
                        factor = filter_config.get('factor', 1.2)
                        enhancer = ImageEnhance.Brightness(img)
                        img = enhancer.enhance(factor)
                    
                    elif filter_type == 'contrast':
                        factor = filter_config.get('factor', 1.2)
                        enhancer = ImageEnhance.Contrast(img)
                        img = enhancer.enhance(factor)
                    
                    elif filter_type == 'saturation':
                        factor = filter_config.get('factor', 1.2)
                        enhancer = ImageEnhance.Color(img)
                        img = enhancer.enhance(factor)
                    
                    elif filter_type == 'grayscale':
                        img = img.convert('L').convert('RGB')
                
                # Save filtered image
                filtered_filename = f"filtered_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
                filtered_path = self.output_dir / filtered_filename
                
                img.save(filtered_path, 'PNG')
            
            return {
                'success': True,
                'filtered_image_path': str(filtered_path),
                'filters_applied': len(filters),
                'file_size': filtered_path.stat().st_size
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _process_generation(self, generation_id: str):
        """Process a generation task"""
        try:
            if generation_id not in self.generation_queue:
                return
            
            task = self.generation_queue[generation_id]
            del self.generation_queue[generation_id]
            
            # Move to active generations
            task['status'] = 'processing'
            task['started_at'] = time.time()
            self.active_generations[generation_id] = task
            
            # Process based on type
            if task['type'] == 'text_to_image':
                result = await self._generate_text_to_image(task)
            elif task['type'] == 'image_to_image':
                result = await self._generate_image_to_image(task)
            elif task['type'] == 'upscale':
                result = await self._upscale_image_task(task)
            else:
                result = {'success': False, 'error': f"Unknown generation type: {task['type']}"}
            
            # Update task with result
            task['status'] = 'completed' if result['success'] else 'failed'
            task['completed_at'] = time.time()
            task['result'] = result
            
            # Cache successful results
            if result['success'] and 'cache_key' in task:
                await self._cache_result(task['cache_key'], result)
            
        except Exception as e:
            self.logger.error(f"Generation processing failed: {e}")
            if generation_id in self.active_generations:
                self.active_generations[generation_id]['status'] = 'failed'
                self.active_generations[generation_id]['error'] = str(e)
    
    async def _generate_text_to_image(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image from text using Stable Diffusion"""
        try:
            if not self.sd_pipeline:
                return {'success': False, 'error': 'Stable Diffusion model not loaded'}
            
            params = task['parameters']
            
            # Set seed for reproducibility
            if params.get('seed'):
                torch.manual_seed(params['seed'])
            
            # Generate image
            with torch.no_grad():
                result = self.sd_pipeline(
                    prompt=params['prompt'],
                    negative_prompt=params['negative_prompt'],
                    width=params['width'],
                    height=params['height'],
                    num_inference_steps=params['num_inference_steps'],
                    guidance_scale=params['guidance_scale'],
                    num_images_per_prompt=params['num_images']
                )
            
            # Save generated images
            image_paths = []
            for i, image in enumerate(result.images):
                filename = f"generated_{task['id']}_{i}_{int(time.time())}.png"
                image_path = self.output_dir / filename
                image.save(image_path)
                image_paths.append(str(image_path))
            
            return {
                'success': True,
                'images': image_paths,
                'parameters': params,
                'generation_time': time.time() - task['started_at']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_image_to_image(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image from image using Stable Diffusion"""
        try:
            if not self.img2img_pipeline:
                return {'success': False, 'error': 'Image-to-image model not loaded'}
            
            params = task['parameters']
            
            # Load source image
            source_image = Image.open(params['source_image']).convert('RGB')
            
            # Set seed for reproducibility
            if params.get('seed'):
                torch.manual_seed(params['seed'])
            
            # Generate image
            with torch.no_grad():
                result = self.img2img_pipeline(
                    prompt=params['prompt'],
                    image=source_image,
                    negative_prompt=params['negative_prompt'],
                    strength=params['strength'],
                    num_inference_steps=params['num_inference_steps'],
                    guidance_scale=params['guidance_scale'],
                    num_images_per_prompt=params['num_images']
                )
            
            # Save generated images
            image_paths = []
            for i, image in enumerate(result.images):
                filename = f"img2img_{task['id']}_{i}_{int(time.time())}.png"
                image_path = self.output_dir / filename
                image.save(image_path)
                image_paths.append(str(image_path))
            
            return {
                'success': True,
                'images': image_paths,
                'parameters': params,
                'generation_time': time.time() - task['started_at']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _upscale_image_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Upscale image task"""
        try:
            if not PIL_AVAILABLE:
                return {'success': False, 'error': 'PIL not available'}
            
            params = task['parameters']
            
            # Load and upscale image
            with Image.open(params['source_image']) as img:
                original_size = img.size
                new_size = (
                    int(original_size[0] * params['scale_factor']),
                    int(original_size[1] * params['scale_factor'])
                )
                
                # Choose resampling method
                if params['method'] == 'lanczos':
                    resampling = Image.Resampling.LANCZOS
                elif params['method'] == 'bicubic':
                    resampling = Image.Resampling.BICUBIC
                else:
                    resampling = Image.Resampling.LANCZOS
                
                # Upscale
                upscaled_img = img.resize(new_size, resampling)
                
                # Save upscaled image
                filename = f"upscaled_{task['id']}_{int(time.time())}.png"
                image_path = self.output_dir / filename
                upscaled_img.save(image_path)
            
            return {
                'success': True,
                'upscaled_image': str(image_path),
                'original_size': original_size,
                'new_size': new_size,
                'scale_factor': params['scale_factor']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _initialize_models(self):
        """Initialize AI models"""
        try:
            if not DIFFUSERS_AVAILABLE:
                self.logger.warning("Diffusers not available, skipping model initialization")
                return
            
            self.logger.info("Initializing Stable Diffusion models...")
            
            # Try to load a lightweight model first
            model_id = "runwayml/stable-diffusion-v1-5"
            
            try:
                # Load text-to-image pipeline
                self.sd_pipeline = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    cache_dir=str(self.models_dir)
                )
                self.sd_pipeline = self.sd_pipeline.to(self.device)
                
                # Load image-to-image pipeline
                self.img2img_pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    cache_dir=str(self.models_dir)
                )
                self.img2img_pipeline = self.img2img_pipeline.to(self.device)
                
                # Enable memory efficient attention if available
                if hasattr(self.sd_pipeline, 'enable_attention_slicing'):
                    self.sd_pipeline.enable_attention_slicing()
                    self.img2img_pipeline.enable_attention_slicing()
                
                self.logger.info("Stable Diffusion models loaded successfully")
                
            except Exception as e:
                self.logger.warning(f"Failed to load full Stable Diffusion models: {e}")
                # Try to load a smaller model or continue without
                self.sd_pipeline = None
                self.img2img_pipeline = None
            
        except Exception as e:
            self.logger.error(f"Model initialization failed: {e}")
    
    async def _check_dependencies(self):
        """Check and install dependencies"""
        try:
            # Check PIL
            if not PIL_AVAILABLE:
                try:
                    import subprocess
                    import sys
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow'])
                    
                    global PIL_AVAILABLE
                    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
                    PIL_AVAILABLE = True
                    self.logger.info("PIL installed successfully")
                except:
                    self.logger.warning("Failed to install PIL")
            
            # Check diffusers (optional - heavy dependency)
            if not DIFFUSERS_AVAILABLE:
                self.logger.info("Diffusers not available - AI image generation will be limited")
                # Don't auto-install diffusers as it's a large dependency
            
        except Exception as e:
            self.logger.error(f"Dependency check failed: {e}")
    
    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key for parameters"""
        # Create a hash of the parameters
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()
    
    async def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check if result is cached"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cached files still exist
                if all(Path(img_path).exists() for img_path in cached_data.get('images', [])):
                    return cached_data
                else:
                    # Remove invalid cache
                    cache_file.unlink()
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Cache check failed: {e}")
            return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache generation result"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            # Only cache successful results with images
            if result.get('success') and result.get('images'):
                cache_data = {
                    'images': result['images'],
                    'parameters': result.get('parameters', {}),
                    'cached_at': time.time()
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)
            
        except Exception as e:
            self.logger.warning(f"Failed to cache result: {e}")
    
    def _estimate_generation_time(self, params: Dict[str, Any]) -> int:
        """Estimate generation time in seconds"""
        base_time = 10  # Base time in seconds
        
        # Adjust based on parameters
        steps_factor = params.get('num_inference_steps', 20) / 20
        size_factor = (params.get('width', 512) * params.get('height', 512)) / (512 * 512)
        num_images_factor = params.get('num_images', 1)
        
        estimated_time = base_time * steps_factor * size_factor * num_images_factor
        
        # Adjust for device
        if self.device == "cpu":
            estimated_time *= 5  # CPU is much slower
        
        return int(estimated_time)
    
    async def cancel_generation(self, generation_id: str) -> bool:
        """Cancel a generation task"""
        if generation_id in self.generation_queue:
            del self.generation_queue[generation_id]
            return True
        
        if generation_id in self.active_generations:
            self.active_generations[generation_id]['status'] = 'cancelled'
            return True
        
        return False
    
    def get_generation_status(self, generation_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a generation"""
        if generation_id in self.generation_queue:
            return self.generation_queue[generation_id]
        
        if generation_id in self.active_generations:
            return self.active_generations[generation_id]
        
        return None
    
    def list_generations(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all generations"""
        return {
            'queued': list(self.generation_queue.values()),
            'active': list(self.active_generations.values())
        }
    
    async def cleanup_old_generations(self, max_age_hours: int = 24):
        """Clean up old generation results"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            # Clean up completed generations
            generations_to_remove = []
            for gen_id, generation in self.active_generations.items():
                if generation.get('completed_at'):
                    if current_time - generation['completed_at'] > max_age_seconds:
                        generations_to_remove.append(gen_id)
            
            for gen_id in generations_to_remove:
                del self.active_generations[gen_id]
            
            # Clean up old cache files
            cache_files_removed = 0
            for cache_file in self.cache_dir.glob("*.json"):
                if current_time - cache_file.stat().st_mtime > max_age_seconds:
                    cache_file.unlink()
                    cache_files_removed += 1
            
            self.logger.info(f"Cleaned up {len(generations_to_remove)} old generations and {cache_files_removed} cache files")
            return len(generations_to_remove) + cache_files_removed
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup generations: {e}")
            return 0
    
    def get_asset_generation_stats(self) -> Dict[str, Any]:
        """Get asset generation statistics"""
        return {
            "diffusers_available": DIFFUSERS_AVAILABLE,
            "pil_available": PIL_AVAILABLE,
            "device": self.device,
            "models_loaded": self.sd_pipeline is not None,
            "queued_generations": len(self.generation_queue),
            "active_generations": len(self.active_generations),
            "cache_files": len(list(self.cache_dir.glob("*.json"))),
            "output_files": len(list(self.output_dir.glob("*"))),
            "cuda_available": torch.cuda.is_available() if DIFFUSERS_AVAILABLE else False
        }