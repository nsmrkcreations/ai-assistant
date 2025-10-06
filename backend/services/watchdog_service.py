"""
Watchdog and Self-Healing Service for AI Assistant
Monitors system health and automatically repairs issues
"""

import asyncio
import logging
import time
import subprocess
import sys
import os
import psutil
import json
import shutil
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime, timedelta
import traceback

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class HealthCheck:
    """Represents a health check"""
    def __init__(self, name: str, check_func: Callable, repair_func: Optional[Callable] = None, 
                 interval: int = 60, critical: bool = False):
        self.name = name
        self.check_func = check_func
        self.repair_func = repair_func
        self.interval = interval
        self.critical = critical
        self.last_check = 0
        self.last_status = True
        self.failure_count = 0
        self.max_failures = 3

class WatchdogService:
    """Watchdog service for monitoring and self-healing"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.health_checks: Dict[str, HealthCheck] = {}
        self.repair_history: List[Dict[str, Any]] = []
        self.system_metrics: Dict[str, Any] = {}
        self.alert_callbacks: List[Callable] = []
        
        # Monitoring intervals
        self.check_interval = 30  # seconds
        self.metrics_interval = 60  # seconds
        
        # Initialize health checks
        self._initialize_health_checks()
        
    async def start(self):
        """Start the watchdog service"""
        try:
            self.is_running = True
            self.logger.info("Watchdog Service started")
            
            # Start monitoring tasks
            asyncio.create_task(self._monitoring_loop())
            asyncio.create_task(self._metrics_collection_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to start watchdog service: {e}")
            raise
    
    async def stop(self):
        """Stop the watchdog service"""
        self.is_running = False
        self.logger.info("Watchdog Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            failed_checks = [name for name, check in self.health_checks.items() 
                           if not check.last_status]
            
            status = ServiceStatus.HEALTHY
            if failed_checks:
                critical_failed = any(self.health_checks[name].critical for name in failed_checks)
                status = ServiceStatus.OFFLINE if critical_failed else ServiceStatus.DEGRADED
            
            return ComponentStatus(
                name="watchdog_service",
                status=status,
                details={
                    "active_checks": len(self.health_checks),
                    "failed_checks": failed_checks,
                    "repair_count": len(self.repair_history),
                    "system_metrics": self.system_metrics,
                    "uptime": time.time() - getattr(self, 'start_time', time.time())
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="watchdog_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    def add_health_check(self, name: str, check_func: Callable, repair_func: Optional[Callable] = None,
                        interval: int = 60, critical: bool = False):
        """Add a health check"""
        self.health_checks[name] = HealthCheck(name, check_func, repair_func, interval, critical)
        self.logger.info(f"Added health check: {name}")
    
    def remove_health_check(self, name: str):
        """Remove a health check"""
        if name in self.health_checks:
            del self.health_checks[name]
            self.logger.info(f"Removed health check: {name}")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        self.start_time = time.time()
        
        while self.is_running:
            try:
                current_time = time.time()
                
                for name, check in self.health_checks.items():
                    if current_time - check.last_check >= check.interval:
                        await self._run_health_check(check)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _metrics_collection_loop(self):
        """System metrics collection loop"""
        while self.is_running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.metrics_interval)
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.metrics_interval)
    
    async def _run_health_check(self, check: HealthCheck):
        """Run a single health check"""
        try:
            check.last_check = time.time()
            
            # Run the check
            if asyncio.iscoroutinefunction(check.check_func):
                result = await check.check_func()
            else:
                result = check.check_func()
            
            if result:
                # Check passed
                if not check.last_status:
                    self.logger.info(f"Health check recovered: {check.name}")
                    await self._send_alert(f"Health check recovered: {check.name}", "info")
                
                check.last_status = True
                check.failure_count = 0
            else:
                # Check failed
                check.failure_count += 1
                
                if check.last_status:
                    self.logger.warning(f"Health check failed: {check.name}")
                    await self._send_alert(f"Health check failed: {check.name}", "warning")
                
                check.last_status = False
                
                # Attempt repair if available and failure count exceeded
                if check.repair_func and check.failure_count >= check.max_failures:
                    await self._attempt_repair(check)
                
        except Exception as e:
            self.logger.error(f"Error running health check {check.name}: {e}")
            check.last_status = False
    
    async def _attempt_repair(self, check: HealthCheck):
        """Attempt to repair a failed health check"""
        try:
            self.logger.info(f"Attempting repair for: {check.name}")
            
            repair_start = time.time()
            
            # Run repair function
            if asyncio.iscoroutinefunction(check.repair_func):
                repair_result = await check.repair_func()
            else:
                repair_result = check.repair_func()
            
            repair_time = time.time() - repair_start
            
            # Log repair attempt
            repair_record = {
                "timestamp": datetime.now().isoformat(),
                "check_name": check.name,
                "repair_time": repair_time,
                "success": repair_result,
                "failure_count": check.failure_count
            }
            
            self.repair_history.append(repair_record)
            
            # Keep repair history manageable
            if len(self.repair_history) > 100:
                self.repair_history = self.repair_history[-50:]
            
            if repair_result:
                self.logger.info(f"Repair successful for: {check.name}")
                await self._send_alert(f"Auto-repair successful: {check.name}", "success")
                check.failure_count = 0
            else:
                self.logger.error(f"Repair failed for: {check.name}")
                await self._send_alert(f"Auto-repair failed: {check.name}", "error")
                
                # If critical and repair failed, escalate
                if check.critical:
                    await self._escalate_critical_failure(check)
            
        except Exception as e:
            self.logger.error(f"Error during repair of {check.name}: {e}")
            await self._send_alert(f"Repair error for {check.name}: {str(e)}", "error")
    
    async def _escalate_critical_failure(self, check: HealthCheck):
        """Escalate critical failures"""
        self.logger.critical(f"Critical system failure: {check.name}")
        
        # Send critical alert
        await self._send_alert(f"CRITICAL: System failure in {check.name}", "critical")
        
        # Could implement additional escalation logic here
        # e.g., restart entire service, send notifications, etc.
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Process info
            process = psutil.Process()
            process_info = {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else 0
            }
            
            self.system_metrics = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": memory.total / 1024 / 1024 / 1024,
                    "available_gb": memory.available / 1024 / 1024 / 1024,
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / 1024 / 1024 / 1024,
                    "free_gb": disk.free / 1024 / 1024 / 1024,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv
                },
                "process": process_info
            }
            
            # Check for resource issues
            await self._check_resource_usage()
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    async def _check_resource_usage(self):
        """Check for resource usage issues"""
        metrics = self.system_metrics
        
        # Check CPU usage
        if metrics["cpu_percent"] > 90:
            await self._send_alert("High CPU usage detected", "warning")
        
        # Check memory usage
        if metrics["memory"]["percent"] > 90:
            await self._send_alert("High memory usage detected", "warning")
        
        # Check disk usage
        if metrics["disk"]["percent"] > 90:
            await self._send_alert("Low disk space detected", "warning")
        
        # Check process resource usage
        if metrics["process"]["memory_mb"] > 1000:  # 1GB
            await self._send_alert("High process memory usage", "warning")
    
    async def _send_alert(self, message: str, level: str):
        """Send alert to registered callbacks"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level
        }
        
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Error sending alert: {e}")
    
    def _initialize_health_checks(self):
        """Initialize default health checks"""
        
        # Python dependencies check
        self.add_health_check(
            "python_dependencies",
            self._check_python_dependencies,
            self._repair_python_dependencies,
            interval=300,  # 5 minutes
            critical=True
        )
        
        # Disk space check
        self.add_health_check(
            "disk_space",
            self._check_disk_space,
            self._repair_disk_space,
            interval=600,  # 10 minutes
            critical=False
        )
        
        # Memory usage check
        self.add_health_check(
            "memory_usage",
            self._check_memory_usage,
            self._repair_memory_usage,
            interval=120,  # 2 minutes
            critical=False
        )
        
        # Configuration files check
        self.add_health_check(
            "config_files",
            self._check_config_files,
            self._repair_config_files,
            interval=300,  # 5 minutes
            critical=True
        )
        
        # Service connectivity check
        self.add_health_check(
            "service_connectivity",
            self._check_service_connectivity,
            self._repair_service_connectivity,
            interval=60,  # 1 minute
            critical=False
        )
    
    def _check_python_dependencies(self) -> bool:
        """Check if required Python packages are installed"""
        try:
            required_packages = [
                'fastapi', 'uvicorn', 'websockets', 'aiofiles',
                'psutil', 'asyncio', 'pathlib'
            ]
            
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    self.logger.warning(f"Missing package: {package}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking dependencies: {e}")
            return False
    
    def _repair_python_dependencies(self) -> bool:
        """Repair missing Python dependencies"""
        try:
            self.logger.info("Attempting to repair Python dependencies")
            
            # Install missing packages
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info("Dependencies repaired successfully")
                return True
            else:
                self.logger.error(f"Failed to repair dependencies: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error repairing dependencies: {e}")
            return False
    
    def _check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            # Fail if less than 10% free space
            return free_percent > 10
            
        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            return False
    
    def _repair_disk_space(self) -> bool:
        """Attempt to free up disk space"""
        try:
            self.logger.info("Attempting to free up disk space")
            
            # Clean up temporary files
            temp_dir = Path.home() / '.cache' / 'ai-assistant'
            if temp_dir.exists():
                for file in temp_dir.glob('*'):
                    if file.is_file() and time.time() - file.stat().st_mtime > 86400:  # 1 day old
                        file.unlink()
            
            # Clean up old log files
            log_dir = self.config.get_logs_path()
            if log_dir.exists():
                for log_file in log_dir.glob('*.log'):
                    if time.time() - log_file.stat().st_mtime > 604800:  # 1 week old
                        log_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning disk space: {e}")
            return False
    
    def _check_memory_usage(self) -> bool:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            # Fail if memory usage is above 95%
            return memory.percent < 95
            
        except Exception as e:
            self.logger.error(f"Error checking memory usage: {e}")
            return False
    
    def _repair_memory_usage(self) -> bool:
        """Attempt to reduce memory usage"""
        try:
            self.logger.info("Attempting to reduce memory usage")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Could implement more aggressive memory cleanup here
            return True
            
        except Exception as e:
            self.logger.error(f"Error reducing memory usage: {e}")
            return False
    
    def _check_config_files(self) -> bool:
        """Check if configuration files exist and are valid"""
        try:
            config_files = [
                self.config.config_file,
                # Add other critical config files
            ]
            
            for config_file in config_files:
                if not Path(config_file).exists():
                    return False
                
                # Try to load and validate config
                try:
                    with open(config_file, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking config files: {e}")
            return False
    
    def _repair_config_files(self) -> bool:
        """Repair missing or corrupted config files"""
        try:
            self.logger.info("Attempting to repair config files")
            
            # Restore from backup or create default config
            config_file = Path(self.config.config_file)
            
            if not config_file.exists() or not self._is_valid_json(config_file):
                # Create default config
                default_config = {
                    "version": "1.0.0",
                    "created": datetime.now().isoformat(),
                    "settings": {}
                }
                
                config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error repairing config files: {e}")
            return False
    
    def _check_service_connectivity(self) -> bool:
        """Check connectivity to external services"""
        try:
            # This is a placeholder - implement actual service checks
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking service connectivity: {e}")
            return False
    
    def _repair_service_connectivity(self) -> bool:
        """Repair service connectivity issues"""
        try:
            self.logger.info("Attempting to repair service connectivity")
            
            # Restart network-related services or clear caches
            return True
            
        except Exception as e:
            self.logger.error(f"Error repairing service connectivity: {e}")
            return False
    
    def _is_valid_json(self, file_path: Path) -> bool:
        """Check if file contains valid JSON"""
        try:
            with open(file_path, 'r') as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "service_status": "running" if self.is_running else "stopped",
            "health_checks": {
                name: {
                    "status": "healthy" if check.last_status else "failed",
                    "last_check": check.last_check,
                    "failure_count": check.failure_count,
                    "critical": check.critical
                }
                for name, check in self.health_checks.items()
            },
            "system_metrics": self.system_metrics,
            "repair_history": self.repair_history[-10:],  # Last 10 repairs
            "uptime": time.time() - getattr(self, 'start_time', time.time())
        }
    
    def get_repair_history(self) -> List[Dict[str, Any]]:
        """Get repair history"""
        return self.repair_history.copy()
    
    async def force_health_check(self, check_name: Optional[str] = None):
        """Force run health checks"""
        if check_name:
            if check_name in self.health_checks:
                await self._run_health_check(self.health_checks[check_name])
        else:
            for check in self.health_checks.values():
                await self._run_health_check(check)
    
    async def emergency_repair(self):
        """Run emergency repair procedures"""
        self.logger.warning("Running emergency repair procedures")
        
        try:
            # Run all repair functions
            for check in self.health_checks.values():
                if check.repair_func and not check.last_status:
                    await self._attempt_repair(check)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear caches
            await self._clear_caches()
            
            self.logger.info("Emergency repair completed")
            
        except Exception as e:
            self.logger.error(f"Emergency repair failed: {e}")
    
    async def _clear_caches(self):
        """Clear various caches"""
        try:
            # Clear temporary files
            temp_dirs = [
                self.config.get_temp_path(),
                Path.home() / '.cache' / 'ai-assistant'
            ]
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    for item in temp_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
            
        except Exception as e:
            self.logger.error(f"Error clearing caches: {e}")