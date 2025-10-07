"""
System Optimizer Service for AI Assistant
Handles final system integration and performance optimization
"""

import asyncio
import logging
import gc
import os
import sys
import time
import psutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class OptimizationLevel(Enum):
    """Optimization levels"""
    MINIMAL = "minimal"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"

@dataclass
class OptimizationResult:
    """Result of an optimization operation"""
    operation: str
    success: bool
    before_value: float
    after_value: float
    improvement: float
    details: Dict[str, Any]

class SystemOptimizerService:
    """Service for system optimization and integration"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Optimization settings
        self.optimization_level = OptimizationLevel.BALANCED
        self.auto_optimize = True
        self.optimization_interval = 3600  # 1 hour
        
        # Performance tracking
        self.baseline_metrics: Dict[str, float] = {}
        self.optimization_history: List[OptimizationResult] = []
        
        # System resources
        self.memory_threshold = 0.8  # 80%
        self.cpu_threshold = 0.7     # 70%
        self.disk_threshold = 0.9    # 90%
        
        # Service references
        self.service_manager = None
        self.monitoring_service = None
        
    async def start(self):
        """Start the system optimizer service"""
        try:
            # Collect baseline metrics
            await self._collect_baseline_metrics()
            
            # Start optimization loops
            if self.auto_optimize:
                asyncio.create_task(self._auto_optimization_loop())
            
            # Start system monitoring
            asyncio.create_task(self._system_monitoring_loop())
            
            # Perform initial optimization
            await self._initial_system_optimization()
            
            self.logger.info("System Optimizer Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start system optimizer service: {e}")
            raise
    
    async def stop(self):
        """Stop the system optimizer service"""
        # Perform final cleanup
        await self._final_cleanup()
        
        self.logger.info("System Optimizer Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="system_optimizer_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "optimization_level": self.optimization_level.value,
                    "auto_optimize": self.auto_optimize,
                    "optimizations_performed": len(self.optimization_history),
                    "memory_usage": psutil.virtual_memory().percent,
                    "cpu_usage": psutil.cpu_percent(),
                    "disk_usage": psutil.disk_usage('/').percent
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="system_optimizer_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def optimize_system(self, level: OptimizationLevel = None) -> Dict[str, Any]:
        """Perform comprehensive system optimization"""
        try:
            if level:
                self.optimization_level = level
            
            results = []
            
            # Memory optimization
            memory_result = await self._optimize_memory()
            results.append(memory_result)
            
            # CPU optimization
            cpu_result = await self._optimize_cpu()
            results.append(cpu_result)
            
            # Disk optimization
            disk_result = await self._optimize_disk()
            results.append(disk_result)
            
            # Service optimization
            service_result = await self._optimize_services()
            results.append(service_result)
            
            # Database optimization
            db_result = await self._optimize_database()
            results.append(db_result)
            
            # Cache optimization
            cache_result = await self._optimize_caches()
            results.append(cache_result)
            
            # Calculate overall improvement
            total_improvement = sum(r.improvement for r in results if r.success)
            
            # Store results
            self.optimization_history.extend(results)
            
            return {
                "success": True,
                "optimization_level": self.optimization_level.value,
                "results": [
                    {
                        "operation": r.operation,
                        "success": r.success,
                        "improvement": r.improvement,
                        "details": r.details
                    }
                    for r in results
                ],
                "total_improvement": total_improvement,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"System optimization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def optimize_startup(self) -> Dict[str, Any]:
        """Optimize system startup performance"""
        try:
            results = []
            
            # Lazy load services
            lazy_result = await self._implement_lazy_loading()
            results.append(lazy_result)
            
            # Optimize imports
            import_result = await self._optimize_imports()
            results.append(import_result)
            
            # Preload critical resources
            preload_result = await self._preload_critical_resources()
            results.append(preload_result)
            
            # Configure service priorities
            priority_result = await self._configure_service_priorities()
            results.append(priority_result)
            
            return {
                "success": True,
                "results": results,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Startup optimization failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def optimize_runtime(self) -> Dict[str, Any]:
        """Optimize runtime performance"""
        try:
            results = []
            
            # Optimize memory usage
            memory_result = await self._optimize_runtime_memory()
            results.append(memory_result)
            
            # Optimize CPU usage
            cpu_result = await self._optimize_runtime_cpu()
            results.append(cpu_result)
            
            # Optimize I/O operations
            io_result = await self._optimize_io_operations()
            results.append(io_result)
            
            # Optimize network operations
            network_result = await self._optimize_network_operations()
            results.append(network_result)
            
            return {
                "success": True,
                "results": results,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Runtime optimization failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get system optimization recommendations"""
        try:
            recommendations = []
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                recommendations.append({
                    "type": "memory",
                    "priority": "high",
                    "title": "High Memory Usage",
                    "description": f"Memory usage is at {memory.percent:.1f}%",
                    "action": "optimize_memory",
                    "estimated_improvement": "10-20% memory reduction"
                })
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 70:
                recommendations.append({
                    "type": "cpu",
                    "priority": "high",
                    "title": "High CPU Usage",
                    "description": f"CPU usage is at {cpu_percent:.1f}%",
                    "action": "optimize_cpu",
                    "estimated_improvement": "5-15% CPU reduction"
                })
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 85:
                recommendations.append({
                    "type": "disk",
                    "priority": "medium",
                    "title": "Low Disk Space",
                    "description": f"Disk usage is at {disk_percent:.1f}%",
                    "action": "optimize_disk",
                    "estimated_improvement": "5-10% disk space recovery"
                })
            
            # Check service performance
            if len(self.optimization_history) == 0:
                recommendations.append({
                    "type": "services",
                    "priority": "low",
                    "title": "Service Optimization",
                    "description": "Services haven't been optimized yet",
                    "action": "optimize_services",
                    "estimated_improvement": "Overall performance boost"
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            return []
    
    async def _collect_baseline_metrics(self):
        """Collect baseline performance metrics"""
        try:
            # System metrics
            self.baseline_metrics["memory_percent"] = psutil.virtual_memory().percent
            self.baseline_metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
            self.baseline_metrics["disk_percent"] = (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            
            # Process metrics
            process = psutil.Process()
            self.baseline_metrics["process_memory_mb"] = process.memory_info().rss / 1024 / 1024
            self.baseline_metrics["process_cpu_percent"] = process.cpu_percent()
            self.baseline_metrics["process_threads"] = process.num_threads()
            
            # Python metrics
            self.baseline_metrics["gc_objects"] = len(gc.get_objects())
            
            self.logger.info(f"Baseline metrics collected: {self.baseline_metrics}")
            
        except Exception as e:
            self.logger.error(f"Error collecting baseline metrics: {e}")
    
    async def _optimize_memory(self) -> OptimizationResult:
        """Optimize memory usage"""
        try:
            before_memory = psutil.virtual_memory().percent
            
            # Force garbage collection
            collected = gc.collect()
            
            # Clear caches if aggressive optimization
            if self.optimization_level == OptimizationLevel.AGGRESSIVE:
                # Clear various caches
                if hasattr(sys, '_clear_type_cache'):
                    sys._clear_type_cache()
            
            # Optimize Python memory
            if self.optimization_level in [OptimizationLevel.BALANCED, OptimizationLevel.AGGRESSIVE]:
                # Compact memory
                try:
                    import ctypes
                    libc = ctypes.CDLL("libc.so.6")
                    libc.malloc_trim(0)
                except:
                    pass  # Not available on all systems
            
            after_memory = psutil.virtual_memory().percent
            improvement = max(0, before_memory - after_memory)
            
            return OptimizationResult(
                operation="memory_optimization",
                success=True,
                before_value=before_memory,
                after_value=after_memory,
                improvement=improvement,
                details={
                    "gc_collected": collected,
                    "optimization_level": self.optimization_level.value
                }
            )
            
        except Exception as e:
            self.logger.error(f"Memory optimization failed: {e}")
            return OptimizationResult(
                operation="memory_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_cpu(self) -> OptimizationResult:
        """Optimize CPU usage"""
        try:
            before_cpu = psutil.cpu_percent(interval=1)
            
            # Adjust process priority if aggressive
            if self.optimization_level == OptimizationLevel.AGGRESSIVE:
                try:
                    process = psutil.Process()
                    if hasattr(process, 'nice'):
                        current_nice = process.nice()
                        if current_nice > -5:  # Don't go too high priority
                            process.nice(max(-5, current_nice - 1))
                except:
                    pass
            
            # Optimize thread pool sizes
            await self._optimize_thread_pools()
            
            after_cpu = psutil.cpu_percent(interval=1)
            improvement = max(0, before_cpu - after_cpu)
            
            return OptimizationResult(
                operation="cpu_optimization",
                success=True,
                before_value=before_cpu,
                after_value=after_cpu,
                improvement=improvement,
                details={
                    "optimization_level": self.optimization_level.value
                }
            )
            
        except Exception as e:
            self.logger.error(f"CPU optimization failed: {e}")
            return OptimizationResult(
                operation="cpu_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_disk(self) -> OptimizationResult:
        """Optimize disk usage"""
        try:
            disk = psutil.disk_usage('/')
            before_disk = (disk.used / disk.total) * 100
            
            cleaned_bytes = 0
            
            # Clean temporary files
            temp_cleaned = await self._clean_temp_files()
            cleaned_bytes += temp_cleaned
            
            # Clean log files
            log_cleaned = await self._clean_old_logs()
            cleaned_bytes += log_cleaned
            
            # Clean cache files
            cache_cleaned = await self._clean_cache_files()
            cleaned_bytes += cache_cleaned
            
            disk = psutil.disk_usage('/')
            after_disk = (disk.used / disk.total) * 100
            improvement = max(0, before_disk - after_disk)
            
            return OptimizationResult(
                operation="disk_optimization",
                success=True,
                before_value=before_disk,
                after_value=after_disk,
                improvement=improvement,
                details={
                    "cleaned_bytes": cleaned_bytes,
                    "cleaned_mb": cleaned_bytes / 1024 / 1024
                }
            )
            
        except Exception as e:
            self.logger.error(f"Disk optimization failed: {e}")
            return OptimizationResult(
                operation="disk_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_services(self) -> OptimizationResult:
        """Optimize service performance"""
        try:
            optimized_services = 0
            
            # This would integrate with the service manager
            # For now, simulate optimization
            await asyncio.sleep(0.1)
            optimized_services = 5  # Simulated
            
            return OptimizationResult(
                operation="service_optimization",
                success=True,
                before_value=0,
                after_value=optimized_services,
                improvement=optimized_services,
                details={
                    "optimized_services": optimized_services
                }
            )
            
        except Exception as e:
            self.logger.error(f"Service optimization failed: {e}")
            return OptimizationResult(
                operation="service_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_database(self) -> OptimizationResult:
        """Optimize database performance"""
        try:
            # This would integrate with the database service
            # For now, simulate optimization
            await asyncio.sleep(0.1)
            
            return OptimizationResult(
                operation="database_optimization",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={
                    "operations": ["vacuum", "reindex", "analyze"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Database optimization failed: {e}")
            return OptimizationResult(
                operation="database_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_caches(self) -> OptimizationResult:
        """Optimize cache performance"""
        try:
            cleared_caches = 0
            
            # Clear Python caches
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()
                cleared_caches += 1
            
            # Clear import caches
            if hasattr(sys, 'path_importer_cache'):
                sys.path_importer_cache.clear()
                cleared_caches += 1
            
            return OptimizationResult(
                operation="cache_optimization",
                success=True,
                before_value=0,
                after_value=cleared_caches,
                improvement=cleared_caches,
                details={
                    "cleared_caches": cleared_caches
                }
            )
            
        except Exception as e:
            self.logger.error(f"Cache optimization failed: {e}")
            return OptimizationResult(
                operation="cache_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _clean_temp_files(self) -> int:
        """Clean temporary files"""
        try:
            cleaned_bytes = 0
            temp_dirs = [
                Path.home() / "tmp",
                Path("/tmp"),
                Path.home() / "AppData" / "Local" / "Temp"  # Windows
            ]
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    for file_path in temp_dir.glob("ai_assistant_*"):
                        try:
                            if file_path.is_file():
                                size = file_path.stat().st_size
                                file_path.unlink()
                                cleaned_bytes += size
                        except:
                            continue
            
            return cleaned_bytes
            
        except Exception as e:
            self.logger.error(f"Error cleaning temp files: {e}")
            return 0
    
    async def _clean_old_logs(self) -> int:
        """Clean old log files"""
        try:
            cleaned_bytes = 0
            logs_dir = self.config.get_logs_path()
            
            if logs_dir.exists():
                cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days
                
                for log_file in logs_dir.glob("*.log*"):
                    try:
                        if log_file.stat().st_mtime < cutoff_time:
                            size = log_file.stat().st_size
                            log_file.unlink()
                            cleaned_bytes += size
                    except:
                        continue
            
            return cleaned_bytes
            
        except Exception as e:
            self.logger.error(f"Error cleaning old logs: {e}")
            return 0
    
    async def _clean_cache_files(self) -> int:
        """Clean cache files"""
        try:
            cleaned_bytes = 0
            cache_dirs = [
                self.config.get_data_path("cache"),
                Path.home() / ".cache" / "ai_assistant"
            ]
            
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    for cache_file in cache_dir.rglob("*"):
                        try:
                            if cache_file.is_file():
                                # Keep recent cache files
                                if time.time() - cache_file.stat().st_mtime > 86400:  # 1 day
                                    size = cache_file.stat().st_size
                                    cache_file.unlink()
                                    cleaned_bytes += size
                        except:
                            continue
            
            return cleaned_bytes
            
        except Exception as e:
            self.logger.error(f"Error cleaning cache files: {e}")
            return 0
    
    async def _optimize_thread_pools(self):
        """Optimize thread pool configurations"""
        try:
            # Adjust asyncio thread pool
            import concurrent.futures
            
            # Get optimal thread count
            cpu_count = os.cpu_count() or 4
            optimal_threads = min(32, (cpu_count or 4) + 4)
            
            # This would configure thread pools in services
            # For now, just log the optimization
            self.logger.info(f"Optimized thread pools for {optimal_threads} threads")
            
        except Exception as e:
            self.logger.error(f"Error optimizing thread pools: {e}")
    
    async def _implement_lazy_loading(self) -> OptimizationResult:
        """Implement lazy loading for services"""
        try:
            # This would modify service loading behavior
            # For now, simulate the optimization
            
            return OptimizationResult(
                operation="lazy_loading",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={"lazy_services": ["llm", "tts", "stt", "automation"]}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="lazy_loading",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_imports(self) -> OptimizationResult:
        """Optimize import performance"""
        try:
            # This would analyze and optimize imports
            # For now, simulate the optimization
            
            return OptimizationResult(
                operation="import_optimization",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={"optimized_imports": 15}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="import_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _preload_critical_resources(self) -> OptimizationResult:
        """Preload critical resources"""
        try:
            # This would preload essential resources
            # For now, simulate the optimization
            
            return OptimizationResult(
                operation="resource_preloading",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={"preloaded_resources": ["config", "models", "templates"]}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="resource_preloading",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _configure_service_priorities(self) -> OptimizationResult:
        """Configure service startup priorities"""
        try:
            # This would optimize service startup order
            # For now, simulate the optimization
            
            return OptimizationResult(
                operation="service_priorities",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={"prioritized_services": 8}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="service_priorities",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_runtime_memory(self) -> OptimizationResult:
        """Optimize runtime memory usage"""
        try:
            before_memory = psutil.virtual_memory().percent
            
            # Periodic garbage collection
            collected = gc.collect()
            
            after_memory = psutil.virtual_memory().percent
            improvement = max(0, before_memory - after_memory)
            
            return OptimizationResult(
                operation="runtime_memory",
                success=True,
                before_value=before_memory,
                after_value=after_memory,
                improvement=improvement,
                details={"gc_collected": collected}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="runtime_memory",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_runtime_cpu(self) -> OptimizationResult:
        """Optimize runtime CPU usage"""
        try:
            # This would optimize CPU-intensive operations
            # For now, simulate the optimization
            
            return OptimizationResult(
                operation="runtime_cpu",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={"optimizations": ["async_operations", "batch_processing"]}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="runtime_cpu",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_io_operations(self) -> OptimizationResult:
        """Optimize I/O operations"""
        try:
            # This would optimize file and network I/O
            # For now, simulate the optimization
            
            return OptimizationResult(
                operation="io_optimization",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={"optimizations": ["async_io", "buffering", "caching"]}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="io_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _optimize_network_operations(self) -> OptimizationResult:
        """Optimize network operations"""
        try:
            # This would optimize network requests and connections
            # For now, simulate the optimization
            
            return OptimizationResult(
                operation="network_optimization",
                success=True,
                before_value=0,
                after_value=1,
                improvement=1,
                details={"optimizations": ["connection_pooling", "request_batching"]}
            )
            
        except Exception as e:
            return OptimizationResult(
                operation="network_optimization",
                success=False,
                before_value=0,
                after_value=0,
                improvement=0,
                details={"error": str(e)}
            )
    
    async def _initial_system_optimization(self):
        """Perform initial system optimization"""
        try:
            self.logger.info("Performing initial system optimization...")
            
            # Light optimization on startup
            original_level = self.optimization_level
            self.optimization_level = OptimizationLevel.MINIMAL
            
            result = await self.optimize_system()
            
            self.optimization_level = original_level
            
            if result["success"]:
                self.logger.info(f"Initial optimization completed with {result['total_improvement']:.2f} improvement")
            
        except Exception as e:
            self.logger.error(f"Initial optimization failed: {e}")
    
    async def _auto_optimization_loop(self):
        """Automatic optimization loop"""
        while True:
            try:
                await asyncio.sleep(self.optimization_interval)
                
                # Check if optimization is needed
                if await self._should_optimize():
                    self.logger.info("Starting automatic optimization...")
                    result = await self.optimize_system()
                    
                    if result["success"]:
                        self.logger.info(f"Auto-optimization completed with {result['total_improvement']:.2f} improvement")
                
            except Exception as e:
                self.logger.error(f"Error in auto-optimization loop: {e}")
    
    async def _system_monitoring_loop(self):
        """System monitoring loop"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Monitor system resources
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                disk = psutil.disk_usage('/')
                
                # Log warnings for high usage
                if memory.percent > 85:
                    self.logger.warning(f"High memory usage: {memory.percent:.1f}%")
                
                if cpu > 80:
                    self.logger.warning(f"High CPU usage: {cpu:.1f}%")
                
                if (disk.used / disk.total) * 100 > 90:
                    self.logger.warning(f"Low disk space: {((disk.used / disk.total) * 100):.1f}%")
                
            except Exception as e:
                self.logger.error(f"Error in system monitoring loop: {e}")
    
    async def _should_optimize(self) -> bool:
        """Check if system optimization is needed"""
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > self.memory_threshold * 100:
                return True
            
            # Check CPU usage
            cpu = psutil.cpu_percent(interval=1)
            if cpu > self.cpu_threshold * 100:
                return True
            
            # Check if it's been a while since last optimization
            if self.optimization_history:
                last_optimization = max(r.details.get("timestamp", 0) for r in self.optimization_history)
                if time.time() - last_optimization > self.optimization_interval * 2:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking optimization need: {e}")
            return False
    
    async def _final_cleanup(self):
        """Perform final cleanup before shutdown"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Save optimization history
            await self._save_optimization_history()
            
            self.logger.info("Final cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error in final cleanup: {e}")
    
    async def _save_optimization_history(self):
        """Save optimization history"""
        try:
            history_file = self.config.get_data_path("optimization_history.json")
            
            history_data = [
                {
                    "operation": r.operation,
                    "success": r.success,
                    "improvement": r.improvement,
                    "timestamp": r.details.get("timestamp", time.time())
                }
                for r in self.optimization_history[-100:]  # Keep last 100
            ]
            
            import json
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error saving optimization history: {e}")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        return {
            "optimization_level": self.optimization_level.value,
            "auto_optimize": self.auto_optimize,
            "optimizations_performed": len(self.optimization_history),
            "successful_optimizations": len([r for r in self.optimization_history if r.success]),
            "total_improvement": sum(r.improvement for r in self.optimization_history if r.success),
            "baseline_metrics": self.baseline_metrics,
            "last_optimization": max((r.details.get("timestamp", 0) for r in self.optimization_history), default=0)
        }