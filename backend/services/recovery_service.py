"""
Error Recovery and Self-Healing Service
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class RecoveryAction(Enum):
    RESTART_SERVICE = "restart_service"
    RESET_CONNECTION = "reset_connection"
    CLEAR_CACHE = "clear_cache"
    RELOAD_CONFIG = "reload_config"
    FALLBACK_MODE = "fallback_mode"
    NOTIFY_ADMIN = "notify_admin"

@dataclass
class RecoveryRule:
    """Recovery rule definition"""
    name: str
    condition: Callable[[Dict], bool]
    action: RecoveryAction
    parameters: Dict[str, Any]
    max_attempts: int = 3
    cooldown: int = 60  # seconds
    priority: int = 1

@dataclass
class RecoveryAttempt:
    """Recovery attempt record"""
    rule_name: str
    action: RecoveryAction
    timestamp: float
    success: bool
    error: Optional[str] = None

class RecoveryService:
    """Self-healing and error recovery service"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.rules: List[RecoveryRule] = []
        self.attempts: Dict[str, List[RecoveryAttempt]] = {}
        self.service_registry: Dict[str, Any] = {}
        self.monitoring_active = False
        self.monitoring_task = None
        
    async def start(self):
        """Start the recovery service"""
        try:
            # Initialize default recovery rules
            self._initialize_default_rules()
            
            # Start monitoring
            self.monitoring_active = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("Recovery Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start Recovery service: {e}")
            raise
    
    async def stop(self):
        """Stop the recovery service"""
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Recovery Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            total_attempts = sum(len(attempts) for attempts in self.attempts.values())
            successful_attempts = sum(
                1 for attempts in self.attempts.values() 
                for attempt in attempts if attempt.success
            )
            
            return ComponentStatus(
                name="recovery_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "monitoring_active": self.monitoring_active,
                    "registered_services": len(self.service_registry),
                    "recovery_rules": len(self.rules),
                    "total_recovery_attempts": total_attempts,
                    "successful_recoveries": successful_attempts,
                    "success_rate": successful_attempts / total_attempts if total_attempts > 0 else 0
                }
            )
                
        except Exception as e:
            return ComponentStatus(
                name="recovery_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    def register_service(self, name: str, service: Any):
        """Register a service for monitoring and recovery"""
        self.service_registry[name] = service
        self.logger.info(f"Registered service for recovery: {name}")
    
    def add_recovery_rule(self, rule: RecoveryRule):
        """Add a recovery rule"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self.logger.info(f"Added recovery rule: {rule.name}")
    
    def _initialize_default_rules(self):
        """Initialize default recovery rules"""
        
        # Service offline recovery
        self.add_recovery_rule(RecoveryRule(
            name="service_offline_restart",
            condition=lambda status: status.get("status") == "offline",
            action=RecoveryAction.RESTART_SERVICE,
            parameters={"service_name": "auto"},
            max_attempts=3,
            cooldown=30,
            priority=10
        ))
        
        # High error rate recovery
        self.add_recovery_rule(RecoveryRule(
            name="high_error_rate_reset",
            condition=lambda status: status.get("error_rate", 0) > 0.5,
            action=RecoveryAction.RESET_CONNECTION,
            parameters={},
            max_attempts=2,
            cooldown=60,
            priority=8
        ))
        
        # Memory leak recovery
        self.add_recovery_rule(RecoveryRule(
            name="memory_leak_restart",
            condition=lambda status: status.get("memory_usage", 0) > 1024 * 1024 * 1024,  # 1GB
            action=RecoveryAction.RESTART_SERVICE,
            parameters={"service_name": "auto"},
            max_attempts=1,
            cooldown=300,
            priority=9
        ))
        
        # Connection timeout recovery
        self.add_recovery_rule(RecoveryRule(
            name="connection_timeout_reset",
            condition=lambda status: "timeout" in status.get("error", "").lower(),
            action=RecoveryAction.RESET_CONNECTION,
            parameters={},
            max_attempts=3,
            cooldown=15,
            priority=7
        ))
        
        # Configuration error recovery
        self.add_recovery_rule(RecoveryRule(
            name="config_error_reload",
            condition=lambda status: "config" in status.get("error", "").lower(),
            action=RecoveryAction.RELOAD_CONFIG,
            parameters={},
            max_attempts=2,
            cooldown=30,
            priority=6
        ))
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self._check_services()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_services(self):
        """Check all registered services"""
        for service_name, service in self.service_registry.items():
            try:
                # Get service status
                if hasattr(service, 'get_status'):
                    status = await service.get_status()
                    status_dict = {
                        "name": service_name,
                        "status": status.status.value if hasattr(status.status, 'value') else str(status.status),
                        "error": getattr(status, 'error', None),
                        "details": getattr(status, 'details', {})
                    }
                else:
                    # Basic health check
                    status_dict = {
                        "name": service_name,
                        "status": "unknown",
                        "error": None,
                        "details": {}
                    }
                
                # Check recovery rules
                await self._apply_recovery_rules(service_name, status_dict)
                
            except Exception as e:
                self.logger.error(f"Error checking service {service_name}: {e}")
                
                # Try to recover from check failure
                await self._apply_recovery_rules(service_name, {
                    "name": service_name,
                    "status": "error",
                    "error": str(e),
                    "details": {}
                })
    
    async def _apply_recovery_rules(self, service_name: str, status: Dict):
        """Apply recovery rules to a service status"""
        for rule in self.rules:
            try:
                # Check if rule condition is met
                if not rule.condition(status):
                    continue
                
                # Check if we've exceeded max attempts
                rule_key = f"{service_name}:{rule.name}"
                attempts = self.attempts.get(rule_key, [])
                
                # Filter recent attempts (within cooldown period)
                current_time = time.time()
                recent_attempts = [
                    a for a in attempts 
                    if current_time - a.timestamp < rule.cooldown
                ]
                
                if len(recent_attempts) >= rule.max_attempts:
                    continue
                
                # Execute recovery action
                success = await self._execute_recovery_action(
                    service_name, rule.action, rule.parameters
                )
                
                # Record attempt
                attempt = RecoveryAttempt(
                    rule_name=rule.name,
                    action=rule.action,
                    timestamp=current_time,
                    success=success
                )
                
                if rule_key not in self.attempts:
                    self.attempts[rule_key] = []
                self.attempts[rule_key].append(attempt)
                
                # Keep only recent attempts
                self.attempts[rule_key] = [
                    a for a in self.attempts[rule_key]
                    if current_time - a.timestamp < 3600  # Keep 1 hour history
                ]
                
                if success:
                    self.logger.info(f"Successfully applied recovery rule {rule.name} to {service_name}")
                    break  # Stop after first successful recovery
                else:
                    self.logger.warning(f"Recovery rule {rule.name} failed for {service_name}")
                
            except Exception as e:
                self.logger.error(f"Error applying recovery rule {rule.name}: {e}")
    
    async def _execute_recovery_action(self, service_name: str, action: RecoveryAction, 
                                     parameters: Dict) -> bool:
        """Execute a recovery action"""
        try:
            service = self.service_registry.get(service_name)
            
            if action == RecoveryAction.RESTART_SERVICE:
                if service and hasattr(service, 'stop') and hasattr(service, 'start'):
                    await service.stop()
                    await asyncio.sleep(1)
                    await service.start()
                    return True
                
            elif action == RecoveryAction.RESET_CONNECTION:
                if service and hasattr(service, 'reset_connection'):
                    await service.reset_connection()
                    return True
                elif service and hasattr(service, 'stop') and hasattr(service, 'start'):
                    # Fallback to restart
                    await service.stop()
                    await asyncio.sleep(0.5)
                    await service.start()
                    return True
                
            elif action == RecoveryAction.CLEAR_CACHE:
                if service and hasattr(service, 'clear_cache'):
                    await service.clear_cache()
                    return True
                
            elif action == RecoveryAction.RELOAD_CONFIG:
                if service and hasattr(service, 'reload_config'):
                    await service.reload_config()
                    return True
                
            elif action == RecoveryAction.FALLBACK_MODE:
                if service and hasattr(service, 'enable_fallback'):
                    await service.enable_fallback()
                    return True
                
            elif action == RecoveryAction.NOTIFY_ADMIN:
                # Log critical error for admin attention
                self.logger.critical(f"Service {service_name} requires admin attention")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing recovery action {action}: {e}")
            return False
    
    async def manual_recovery(self, service_name: str, action: RecoveryAction, 
                            parameters: Dict = None) -> bool:
        """Manually trigger recovery action"""
        try:
            success = await self._execute_recovery_action(
                service_name, action, parameters or {}
            )
            
            # Record manual attempt
            rule_key = f"{service_name}:manual"
            attempt = RecoveryAttempt(
                rule_name="manual",
                action=action,
                timestamp=time.time(),
                success=success
            )
            
            if rule_key not in self.attempts:
                self.attempts[rule_key] = []
            self.attempts[rule_key].append(attempt)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Manual recovery failed: {e}")
            return False
    
    def get_recovery_history(self, service_name: str = None) -> Dict[str, List[Dict]]:
        """Get recovery attempt history"""
        result = {}
        
        for key, attempts in self.attempts.items():
            if service_name and not key.startswith(f"{service_name}:"):
                continue
            
            result[key] = [
                {
                    "rule_name": attempt.rule_name,
                    "action": attempt.action.value,
                    "timestamp": attempt.timestamp,
                    "success": attempt.success,
                    "error": attempt.error
                }
                for attempt in attempts
            ]
        
        return result