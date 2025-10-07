"""
Production Monitoring and Logging Service for AI Assistant
Comprehensive monitoring, logging, and alerting system
"""

import asyncio
import logging
import json
import time
import os
import sys
import traceback
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import threading
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class LogEntry:
    """Represents a log entry"""
    timestamp: float
    level: LogLevel
    service: str
    message: str
    details: Dict[str, Any]
    trace_id: Optional[str] = None
    user_id: Optional[str] = None

@dataclass
class MetricPoint:
    """Represents a metric data point"""
    timestamp: float
    metric_name: str
    value: float
    tags: Dict[str, str]

@dataclass
class Alert:
    """Represents an alert"""
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    service: str
    metric: str
    threshold: float
    current_value: float
    created_at: float
    resolved_at: Optional[float] = None
    acknowledged: bool = False

class MonitoringService:
    """Production monitoring and logging service"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Logging setup
        self.log_buffer: List[LogEntry] = []
        self.log_handlers: Dict[str, logging.Handler] = {}
        self.structured_logger = None
        
        # Metrics collection
        self.metrics_buffer: List[MetricPoint] = []
        self.metric_collectors: Dict[str, Callable] = {}
        self.collection_interval = 30  # seconds
        
        # Alerting
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_handlers: List[Callable] = []
        
        # Performance monitoring
        self.performance_history: List[Dict[str, Any]] = []
        self.error_tracking: Dict[str, List[Dict[str, Any]]] = {}
        
        # Health checks
        self.health_checks: Dict[str, Callable] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
        
        # Setup logging
        self._setup_logging()
        self._setup_metric_collectors()
        self._setup_alert_rules()
        self._setup_health_checks()
        
    async def start(self):
        """Start the monitoring service"""
        try:
            # Start monitoring loops
            asyncio.create_task(self._metrics_collection_loop())
            asyncio.create_task(self._health_check_loop())
            asyncio.create_task(self._alert_processing_loop())
            asyncio.create_task(self._log_processing_loop())
            asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("Monitoring Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring service: {e}")
            raise
    
    async def stop(self):
        """Stop the monitoring service"""
        # Flush remaining logs and metrics
        await self._flush_logs()
        await self._flush_metrics()
        
        self.logger.info("Monitoring Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="monitoring_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "log_buffer_size": len(self.log_buffer),
                    "metrics_buffer_size": len(self.metrics_buffer),
                    "active_alerts": len(self.active_alerts),
                    "health_checks": len(self.health_checks),
                    "error_types": len(self.error_tracking)
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="monitoring_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    def log_event(self, level: LogLevel, service: str, message: str, 
                  details: Dict[str, Any] = None, trace_id: str = None, 
                  user_id: str = None):
        """Log an event"""
        try:
            log_entry = LogEntry(
                timestamp=time.time(),
                level=level,
                service=service,
                message=message,
                details=details or {},
                trace_id=trace_id,
                user_id=user_id
            )
            
            self.log_buffer.append(log_entry)
            
            # Also log to standard logger
            log_level = getattr(logging, level.value)
            self.logger.log(log_level, f"[{service}] {message}", extra={
                "details": details,
                "trace_id": trace_id,
                "user_id": user_id
            })
            
        except Exception as e:
            print(f"Error logging event: {e}")
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric"""
        try:
            metric_point = MetricPoint(
                timestamp=time.time(),
                metric_name=metric_name,
                value=value,
                tags=tags or {}
            )
            
            self.metrics_buffer.append(metric_point)
            
        except Exception as e:
            self.logger.error(f"Error recording metric: {e}")
    
    def track_error(self, service: str, error: Exception, context: Dict[str, Any] = None):
        """Track an error"""
        try:
            error_info = {
                "timestamp": time.time(),
                "service": service,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
                "context": context or {}
            }
            
            if service not in self.error_tracking:
                self.error_tracking[service] = []
            
            self.error_tracking[service].append(error_info)
            
            # Keep only recent errors
            if len(self.error_tracking[service]) > 100:
                self.error_tracking[service] = self.error_tracking[service][-50:]
            
            # Log the error
            self.log_event(
                LogLevel.ERROR,
                service,
                f"Error: {error}",
                {"error_type": type(error).__name__, "context": context}
            )
            
        except Exception as e:
            print(f"Error tracking error: {e}")
    
    def add_alert_rule(self, rule_name: str, metric: str, threshold: float, 
                      comparison: str, severity: AlertSeverity, 
                      description: str = ""):
        """Add an alert rule"""
        try:
            self.alert_rules[rule_name] = {
                "metric": metric,
                "threshold": threshold,
                "comparison": comparison,  # "gt", "lt", "eq"
                "severity": severity,
                "description": description,
                "enabled": True
            }
            
        except Exception as e:
            self.logger.error(f"Error adding alert rule: {e}")
    
    def add_health_check(self, check_name: str, check_function: Callable):
        """Add a health check"""
        try:
            self.health_checks[check_name] = check_function
            
        except Exception as e:
            self.logger.error(f"Error adding health check: {e}")
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the specified time period"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            recent_metrics = [
                metric for metric in self.metrics_buffer
                if metric.timestamp > cutoff_time
            ]
            
            # Group by metric name
            metric_groups = {}
            for metric in recent_metrics:
                if metric.metric_name not in metric_groups:
                    metric_groups[metric.metric_name] = []
                metric_groups[metric.metric_name].append(metric.value)
            
            # Calculate statistics
            summary = {}
            for metric_name, values in metric_groups.items():
                if values:
                    summary[metric_name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "latest": values[-1]
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting metrics summary: {e}")
            return {}
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            summary = {}
            for service, errors in self.error_tracking.items():
                recent_errors = [
                    error for error in errors
                    if error["timestamp"] > cutoff_time
                ]
                
                if recent_errors:
                    error_types = {}
                    for error in recent_errors:
                        error_type = error["error_type"]
                        if error_type not in error_types:
                            error_types[error_type] = 0
                        error_types[error_type] += 1
                    
                    summary[service] = {
                        "total_errors": len(recent_errors),
                        "error_types": error_types,
                        "latest_error": recent_errors[-1] if recent_errors else None
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting error summary: {e}")
            return {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return self.health_status.copy()
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].resolved_at = time.time()
                del self.active_alerts[alert_id]
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error resolving alert: {e}")
            return False
    
    async def _metrics_collection_loop(self):
        """Collect metrics periodically"""
        while True:
            try:
                await asyncio.sleep(self.collection_interval)
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Collect custom metrics
                for collector_name, collector_func in self.metric_collectors.items():
                    try:
                        await collector_func()
                    except Exception as e:
                        self.logger.error(f"Error in metric collector {collector_name}: {e}")
                
                # Flush metrics if buffer is large
                if len(self.metrics_buffer) > 1000:
                    await self._flush_metrics()
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
    
    async def _health_check_loop(self):
        """Run health checks periodically"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for check_name, check_func in self.health_checks.items():
                    try:
                        result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                        
                        self.health_status[check_name] = {
                            "status": "healthy" if result else "unhealthy",
                            "last_check": time.time(),
                            "result": result
                        }
                        
                    except Exception as e:
                        self.health_status[check_name] = {
                            "status": "error",
                            "last_check": time.time(),
                            "error": str(e)
                        }
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
    
    async def _alert_processing_loop(self):
        """Process alerts based on metrics and rules"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check alert rules against recent metrics
                await self._check_alert_rules()
                
                # Process alert notifications
                await self._process_alert_notifications()
                
            except Exception as e:
                self.logger.error(f"Error in alert processing loop: {e}")
    
    async def _log_processing_loop(self):
        """Process and flush logs periodically"""
        while True:
            try:
                await asyncio.sleep(30)  # Process every 30 seconds
                
                if len(self.log_buffer) > 100:
                    await self._flush_logs()
                
            except Exception as e:
                self.logger.error(f"Error in log processing loop: {e}")
    
    async def _cleanup_loop(self):
        """Clean up old data periodically"""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean every hour
                
                current_time = time.time()
                
                # Clean old metrics (keep 7 days)
                cutoff_time = current_time - (7 * 24 * 3600)
                self.metrics_buffer = [
                    metric for metric in self.metrics_buffer
                    if metric.timestamp > cutoff_time
                ]
                
                # Clean old logs (keep 3 days)
                cutoff_time = current_time - (3 * 24 * 3600)
                self.log_buffer = [
                    log for log in self.log_buffer
                    if log.timestamp > cutoff_time
                ]
                
                # Clean old performance history
                cutoff_time = current_time - (24 * 3600)
                self.performance_history = [
                    perf for perf in self.performance_history
                    if perf["timestamp"] > cutoff_time
                ]
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("system.cpu.percent", cpu_percent, {"type": "system"})
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.record_metric("system.memory.percent", memory.percent, {"type": "system"})
            self.record_metric("system.memory.used_mb", memory.used / 1024 / 1024, {"type": "system"})
            self.record_metric("system.memory.available_mb", memory.available / 1024 / 1024, {"type": "system"})
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.record_metric("system.disk.percent", (disk.used / disk.total) * 100, {"type": "system"})
            self.record_metric("system.disk.used_gb", disk.used / 1024 / 1024 / 1024, {"type": "system"})
            self.record_metric("system.disk.free_gb", disk.free / 1024 / 1024 / 1024, {"type": "system"})
            
            # Network metrics
            network = psutil.net_io_counters()
            self.record_metric("system.network.bytes_sent", network.bytes_sent, {"type": "system"})
            self.record_metric("system.network.bytes_recv", network.bytes_recv, {"type": "system"})
            
            # Process metrics
            process = psutil.Process()
            self.record_metric("process.cpu.percent", process.cpu_percent(), {"type": "process"})
            self.record_metric("process.memory.rss_mb", process.memory_info().rss / 1024 / 1024, {"type": "process"})
            self.record_metric("process.threads", process.num_threads(), {"type": "process"})
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    async def _check_alert_rules(self):
        """Check alert rules against current metrics"""
        try:
            current_time = time.time()
            
            # Get recent metrics (last 5 minutes)
            cutoff_time = current_time - 300
            recent_metrics = [
                metric for metric in self.metrics_buffer
                if metric.timestamp > cutoff_time
            ]
            
            # Group by metric name and get latest value
            latest_metrics = {}
            for metric in recent_metrics:
                if (metric.metric_name not in latest_metrics or 
                    metric.timestamp > latest_metrics[metric.metric_name]["timestamp"]):
                    latest_metrics[metric.metric_name] = {
                        "value": metric.value,
                        "timestamp": metric.timestamp
                    }
            
            # Check each alert rule
            for rule_name, rule in self.alert_rules.items():
                if not rule["enabled"]:
                    continue
                
                metric_name = rule["metric"]
                if metric_name not in latest_metrics:
                    continue
                
                current_value = latest_metrics[metric_name]["value"]
                threshold = rule["threshold"]
                comparison = rule["comparison"]
                
                # Check if alert condition is met
                alert_triggered = False
                if comparison == "gt" and current_value > threshold:
                    alert_triggered = True
                elif comparison == "lt" and current_value < threshold:
                    alert_triggered = True
                elif comparison == "eq" and current_value == threshold:
                    alert_triggered = True
                
                # Create alert if triggered and not already active
                if alert_triggered:
                    alert_id = f"{rule_name}_{int(current_time)}"
                    if not any(alert.title == rule_name and not alert.resolved_at 
                             for alert in self.active_alerts.values()):
                        
                        alert = Alert(
                            alert_id=alert_id,
                            severity=rule["severity"],
                            title=rule_name,
                            description=rule["description"],
                            service="monitoring",
                            metric=metric_name,
                            threshold=threshold,
                            current_value=current_value,
                            created_at=current_time
                        )
                        
                        self.active_alerts[alert_id] = alert
                        
                        self.log_event(
                            LogLevel.WARNING,
                            "monitoring",
                            f"Alert triggered: {rule_name}",
                            {
                                "metric": metric_name,
                                "current_value": current_value,
                                "threshold": threshold,
                                "severity": rule["severity"].name
                            }
                        )
            
        except Exception as e:
            self.logger.error(f"Error checking alert rules: {e}")
    
    async def _process_alert_notifications(self):
        """Process alert notifications"""
        try:
            for alert in self.active_alerts.values():
                if not alert.acknowledged and not alert.resolved_at:
                    # Send notifications through registered handlers
                    for handler in self.alert_handlers:
                        try:
                            await handler(alert)
                        except Exception as e:
                            self.logger.error(f"Error in alert handler: {e}")
            
        except Exception as e:
            self.logger.error(f"Error processing alert notifications: {e}")
    
    async def _flush_logs(self):
        """Flush log buffer to storage"""
        try:
            if not self.log_buffer:
                return
            
            # Write to structured log file
            log_file = self.config.get_logs_path() / "structured.log"
            
            with open(log_file, 'a') as f:
                for log_entry in self.log_buffer:
                    log_data = asdict(log_entry)
                    f.write(json.dumps(log_data) + '\n')
            
            self.log_buffer.clear()
            
        except Exception as e:
            print(f"Error flushing logs: {e}")
    
    async def _flush_metrics(self):
        """Flush metrics buffer to storage"""
        try:
            if not self.metrics_buffer:
                return
            
            # Write to metrics file
            metrics_file = self.config.get_logs_path() / "metrics.log"
            
            with open(metrics_file, 'a') as f:
                for metric in self.metrics_buffer:
                    metric_data = asdict(metric)
                    f.write(json.dumps(metric_data) + '\n')
            
            # Keep only recent metrics in memory
            cutoff_time = time.time() - 3600  # Keep 1 hour
            self.metrics_buffer = [
                metric for metric in self.metrics_buffer
                if metric.timestamp > cutoff_time
            ]
            
        except Exception as e:
            self.logger.error(f"Error flushing metrics: {e}")
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        try:
            logs_dir = self.config.get_logs_path()
            logs_dir.mkdir(exist_ok=True)
            
            # Setup rotating file handler for general logs
            general_handler = RotatingFileHandler(
                logs_dir / "ai_assistant.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            general_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            
            # Setup error log handler
            error_handler = RotatingFileHandler(
                logs_dir / "errors.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=10
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(exc_info)s'
            ))
            
            # Setup daily rotating handler
            daily_handler = TimedRotatingFileHandler(
                logs_dir / "daily.log",
                when='midnight',
                interval=1,
                backupCount=30
            )
            daily_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            
            # Add handlers to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(general_handler)
            root_logger.addHandler(error_handler)
            root_logger.addHandler(daily_handler)
            
            self.log_handlers = {
                "general": general_handler,
                "error": error_handler,
                "daily": daily_handler
            }
            
        except Exception as e:
            print(f"Error setting up logging: {e}")
    
    def _setup_metric_collectors(self):
        """Setup custom metric collectors"""
        try:
            # Application-specific metrics collector
            async def collect_app_metrics():
                # Collect application-specific metrics
                self.record_metric("app.log_buffer_size", len(self.log_buffer), {"type": "app"})
                self.record_metric("app.metrics_buffer_size", len(self.metrics_buffer), {"type": "app"})
                self.record_metric("app.active_alerts", len(self.active_alerts), {"type": "app"})
            
            self.metric_collectors["app_metrics"] = collect_app_metrics
            
        except Exception as e:
            self.logger.error(f"Error setting up metric collectors: {e}")
    
    def _setup_alert_rules(self):
        """Setup default alert rules"""
        try:
            # System resource alerts
            self.add_alert_rule(
                "high_cpu_usage",
                "system.cpu.percent",
                80.0,
                "gt",
                AlertSeverity.HIGH,
                "CPU usage is above 80%"
            )
            
            self.add_alert_rule(
                "high_memory_usage",
                "system.memory.percent",
                85.0,
                "gt",
                AlertSeverity.HIGH,
                "Memory usage is above 85%"
            )
            
            self.add_alert_rule(
                "low_disk_space",
                "system.disk.percent",
                90.0,
                "gt",
                AlertSeverity.CRITICAL,
                "Disk usage is above 90%"
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up alert rules: {e}")
    
    def _setup_health_checks(self):
        """Setup default health checks"""
        try:
            def check_disk_space():
                disk = psutil.disk_usage('/')
                return (disk.free / disk.total) > 0.1  # At least 10% free
            
            def check_memory():
                memory = psutil.virtual_memory()
                return memory.percent < 95  # Less than 95% used
            
            def check_cpu():
                cpu_percent = psutil.cpu_percent(interval=1)
                return cpu_percent < 95  # Less than 95% used
            
            self.add_health_check("disk_space", check_disk_space)
            self.add_health_check("memory", check_memory)
            self.add_health_check("cpu", check_cpu)
            
        except Exception as e:
            self.logger.error(f"Error setting up health checks: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring service statistics"""
        return {
            "log_buffer_size": len(self.log_buffer),
            "metrics_buffer_size": len(self.metrics_buffer),
            "active_alerts": len(self.active_alerts),
            "alert_rules": len(self.alert_rules),
            "health_checks": len(self.health_checks),
            "error_services": len(self.error_tracking),
            "collection_interval": self.collection_interval
        }