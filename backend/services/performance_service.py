"""
Performance monitoring and optimization service
"""

import asyncio
import logging
import psutil
import gc
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

@dataclass
class PerformanceMetrics:
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    process_count: int
    thread_count: int
    timestamp: datetime

class PerformanceService:
    """Service for monitoring and optimizing application performance"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics_history: list[PerformanceMetrics] = []
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Performance thresholds
        self.cpu_threshold = 80.0  # %
        self.memory_threshold = 85.0  # %
        self.disk_threshold = 90.0  # %
        
        # Cleanup intervals
        self.gc_interval = 300  # 5 minutes
        self.metrics_retention = 3600  # 1 hour
        
    async def start(self):
        """Start the performance service"""
        try:
            self.monitoring_active = True
            
            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("Performance Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start Performance service: {e}")
            raise
    
    async def stop(self):
        """Stop the performance service"""
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            current_metrics = self.get_current_metrics()
            
            # Determine status based on thresholds
            status = ServiceStatus.HEALTHY
            if (current_metrics.cpu_percent > self.cpu_threshold or 
                current_metrics.memory_percent > self.memory_threshold or
                current_metrics.disk_usage_percent > self.disk_threshold):
                status = ServiceStatus.DEGRADED
            
            return ComponentStatus(
                name="performance_service",
                status=status,
                details={
                    "cpu_percent": current_metrics.cpu_percent,
                    "memory_percent": current_metrics.memory_percent,
                    "memory_used_mb": current_metrics.memory_used_mb,
                    "disk_usage_percent": current_metrics.disk_usage_percent,
                    "process_count": current_metrics.process_count,
                    "metrics_count": len(self.metrics_history)
                }
            )
                
        except Exception as e:
            return ComponentStatus(
                name="performance_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Process info
            process = psutil.Process()
            process_count = len(psutil.pids())
            thread_count = process.num_threads()
            
            return PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                process_count=process_count,
                thread_count=thread_count,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return PerformanceMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                process_count=0,
                thread_count=0,
                timestamp=datetime.now()
            )
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect metrics
                metrics = self.get_current_metrics()
                self.metrics_history.append(metrics)
                
                # Check for performance issues
                await self._check_performance_issues(metrics)
                
                # Clean old metrics
                cutoff_time = datetime.now() - timedelta(seconds=self.metrics_retention)
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m.timestamp > cutoff_time
                ]
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Periodic cleanup loop"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(self.gc_interval)
                
                # Force garbage collection
                collected = gc.collect()
                if collected > 0:
                    self.logger.debug(f"Garbage collector freed {collected} objects")
                
                # Log memory usage after cleanup
                metrics = self.get_current_metrics()
                self.logger.debug(f"Memory usage after cleanup: {metrics.memory_percent:.1f}%")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _check_performance_issues(self, metrics: PerformanceMetrics):
        """Check for performance issues and take action"""
        try:
            # High CPU usage
            if metrics.cpu_percent > self.cpu_threshold:
                self.logger.warning(f"High CPU usage detected: {metrics.cpu_percent:.1f}%")
                await self._handle_high_cpu()
            
            # High memory usage
            if metrics.memory_percent > self.memory_threshold:
                self.logger.warning(f"High memory usage detected: {metrics.memory_percent:.1f}%")
                await self._handle_high_memory()
            
            # High disk usage
            if metrics.disk_usage_percent > self.disk_threshold:
                self.logger.warning(f"High disk usage detected: {metrics.disk_usage_percent:.1f}%")
                await self._handle_high_disk_usage()
                
        except Exception as e:
            self.logger.error(f"Error checking performance issues: {e}")
    
    async def _handle_high_cpu(self):
        """Handle high CPU usage"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Log top processes by CPU
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            top_processes = processes[:5]
            
            self.logger.info(f"Top CPU processes: {top_processes}")
            
        except Exception as e:
            self.logger.error(f"Error handling high CPU: {e}")
    
    async def _handle_high_memory(self):
        """Handle high memory usage"""
        try:
            # Force garbage collection
            collected = gc.collect()
            self.logger.info(f"Forced garbage collection, freed {collected} objects")
            
            # Log memory usage by process
            process = psutil.Process()
            memory_info = process.memory_info()
            
            self.logger.info(f"Process memory - RSS: {memory_info.rss / 1024 / 1024:.1f}MB, "
                           f"VMS: {memory_info.vms / 1024 / 1024:.1f}MB")
            
            # Clear metrics history if too large
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-500:]
                self.logger.info("Cleared old performance metrics to free memory")
                
        except Exception as e:
            self.logger.error(f"Error handling high memory: {e}")
    
    async def _handle_high_disk_usage(self):
        """Handle high disk usage"""
        try:
            # Log disk usage details
            disk_usage = psutil.disk_usage('/')
            self.logger.warning(f"Disk usage - Total: {disk_usage.total / 1024**3:.1f}GB, "
                              f"Used: {disk_usage.used / 1024**3:.1f}GB, "
                              f"Free: {disk_usage.free / 1024**3:.1f}GB")
            
            # Could trigger cleanup of temporary files, logs, etc.
            # For now, just log the warning
            
        except Exception as e:
            self.logger.error(f"Error handling high disk usage: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
        
        return {
            "current": {
                "cpu_percent": recent_metrics[-1].cpu_percent,
                "memory_percent": recent_metrics[-1].memory_percent,
                "memory_used_mb": recent_metrics[-1].memory_used_mb,
                "disk_usage_percent": recent_metrics[-1].disk_usage_percent
            },
            "average": {
                "cpu_percent": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
                "memory_percent": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            },
            "peak": {
                "cpu_percent": max(m.cpu_percent for m in recent_metrics),
                "memory_percent": max(m.memory_percent for m in recent_metrics)
            },
            "metrics_count": len(self.metrics_history),
            "monitoring_duration": (
                recent_metrics[-1].timestamp - self.metrics_history[0].timestamp
            ).total_seconds() if len(self.metrics_history) > 1 else 0
        }
    
    async def optimize_performance(self):
        """Manually trigger performance optimization"""
        try:
            self.logger.info("Starting manual performance optimization...")
            
            # Force garbage collection
            before_gc = gc.get_count()
            collected = gc.collect()
            after_gc = gc.get_count()
            
            self.logger.info(f"Garbage collection - Before: {before_gc}, "
                           f"After: {after_gc}, Collected: {collected}")
            
            # Clear old metrics
            if len(self.metrics_history) > 100:
                old_count = len(self.metrics_history)
                self.metrics_history = self.metrics_history[-50:]
                self.logger.info(f"Cleared {old_count - len(self.metrics_history)} old metrics")
            
            # Get current metrics after optimization
            metrics = self.get_current_metrics()
            self.logger.info(f"Performance after optimization - "
                           f"CPU: {metrics.cpu_percent:.1f}%, "
                           f"Memory: {metrics.memory_percent:.1f}%")
            
            return {
                "status": "success",
                "collected_objects": collected,
                "current_metrics": {
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": metrics.memory_percent,
                    "memory_used_mb": metrics.memory_used_mb
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error during performance optimization: {e}")
            return {"status": "error", "error": str(e)}