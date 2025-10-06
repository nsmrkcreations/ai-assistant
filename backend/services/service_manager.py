"""
Service Integration Manager for coordinating all backend services
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass
from enum import Enum

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class ServiceInfo:
    name: str
    instance: Any
    state: ServiceState
    dependencies: List[str]
    startup_order: int
    last_health_check: Optional[float] = None
    error_count: int = 0

class ServiceManager:
    """Manages all backend services with proper initialization, monitoring, and coordination"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.services: Dict[str, ServiceInfo] = {}
        self.startup_order: List[str] = []
        self.health_check_interval = 30  # seconds
        self.monitoring_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
        
    def register_service(self, name: str, service_class: Type, dependencies: List[str] = None, 
                        startup_order: int = 100) -> None:
        """Register a service with the manager"""
        try:
            # Create service instance
            service_instance = service_class(self.config)
            
            # Register service info
            self.services[name] = ServiceInfo(
                name=name,
                instance=service_instance,
                state=ServiceState.STOPPED,
                dependencies=dependencies or [],
                startup_order=startup_order
            )
            
            self.logger.info(f"Registered service: {name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register service {name}: {e}")
            raise
    
    def register_service_instance(self, name: str, service_instance: Any, 
                                dependencies: List[str] = None, startup_order: int = 100) -> None:
        """Register an existing service instance"""
        self.services[name] = ServiceInfo(
            name=name,
            instance=service_instance,
            state=ServiceState.STOPPED,
            dependencies=dependencies or [],
            startup_order=startup_order
        )
        self.logger.info(f"Registered service instance: {name}")
    
    async def start_all_services(self, allow_partial_failure: bool = False) -> bool:
        """Start all registered services in dependency order"""
        try:
            self.logger.info("Starting all services...")
            
            # Sort services by startup order and dependencies
            sorted_services = self._get_startup_order()
            
            failed_services = []
            started_services = []
            
            # Start services in order
            for service_name in sorted_services:
                if await self._start_service(service_name):
                    started_services.append(service_name)
                    self.logger.info(f"Service {service_name} started successfully")
                else:
                    failed_services.append(service_name)
                    self.logger.error(f"Failed to start service {service_name}")
                    
                    if not allow_partial_failure:
                        return False
            
            # Start health monitoring
            self.monitoring_task = asyncio.create_task(self._health_monitoring_loop())
            
            if failed_services:
                self.logger.warning(f"Services started with failures. Started: {started_services}, Failed: {failed_services}")
                return allow_partial_failure
            else:
                self.logger.info("All services started successfully")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            return False
    
    async def stop_all_services(self) -> None:
        """Stop all services in reverse dependency order"""
        try:
            self.logger.info("Stopping all services...")
            
            # Signal shutdown
            self.shutdown_event.set()
            
            # Stop health monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Get shutdown order (reverse of startup)
            sorted_services = self._get_startup_order()
            sorted_services.reverse()
            
            # Stop services
            for service_name in sorted_services:
                await self._stop_service(service_name)
            
            self.logger.info("All services stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""
        try:
            self.logger.info(f"Restarting service: {service_name}")
            
            if service_name not in self.services:
                self.logger.error(f"Service {service_name} not found")
                return False
            
            # Stop service
            await self._stop_service(service_name)
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Start service
            return await self._start_service(service_name)
            
        except Exception as e:
            self.logger.error(f"Failed to restart service {service_name}: {e}")
            return False
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a service instance by name"""
        service_info = self.services.get(name)
        return service_info.instance if service_info else None
    
    def get_service_status(self, name: str) -> Optional[ComponentStatus]:
        """Get status of a specific service"""
        service_info = self.services.get(name)
        if not service_info:
            return None
        
        try:
            # Get status from service if it has the method
            if hasattr(service_info.instance, 'get_status'):
                return asyncio.create_task(service_info.instance.get_status())
            else:
                # Return basic status
                status = ServiceStatus.HEALTHY if service_info.state == ServiceState.RUNNING else ServiceStatus.OFFLINE
                return ComponentStatus(
                    name=name,
                    status=status,
                    details={"state": service_info.state.value}
                )
        except Exception as e:
            return ComponentStatus(
                name=name,
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def get_all_service_status(self) -> Dict[str, ComponentStatus]:
        """Get status of all services"""
        statuses = {}
        
        for name, service_info in self.services.items():
            try:
                if hasattr(service_info.instance, 'get_status'):
                    status = await service_info.instance.get_status()
                else:
                    service_status = ServiceStatus.HEALTHY if service_info.state == ServiceState.RUNNING else ServiceStatus.OFFLINE
                    status = ComponentStatus(
                        name=name,
                        status=service_status,
                        details={"state": service_info.state.value}
                    )
                statuses[name] = status
            except Exception as e:
                statuses[name] = ComponentStatus(
                    name=name,
                    status=ServiceStatus.OFFLINE,
                    error=str(e)
                )
        
        return statuses
    
    def _get_startup_order(self) -> List[str]:
        """Get services in startup order considering dependencies"""
        # Simple topological sort based on startup_order and dependencies
        services_by_order = sorted(
            self.services.items(),
            key=lambda x: x[1].startup_order
        )
        
        return [name for name, _ in services_by_order]
    
    async def _start_service(self, service_name: str) -> bool:
        """Start a single service"""
        try:
            service_info = self.services[service_name]
            
            if service_info.state == ServiceState.RUNNING:
                return True
            
            self.logger.info(f"Starting service: {service_name}")
            service_info.state = ServiceState.STARTING
            
            # Check dependencies
            for dep_name in service_info.dependencies:
                dep_service = self.services.get(dep_name)
                if not dep_service or dep_service.state != ServiceState.RUNNING:
                    self.logger.error(f"Dependency {dep_name} not running for service {service_name}")
                    service_info.state = ServiceState.ERROR
                    return False
            
            # Start the service
            if hasattr(service_info.instance, 'start'):
                await service_info.instance.start()
            
            service_info.state = ServiceState.RUNNING
            service_info.error_count = 0
            self.logger.info(f"Service {service_name} started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start service {service_name}: {e}")
            self.services[service_name].state = ServiceState.ERROR
            self.services[service_name].error_count += 1
            return False
    
    async def _stop_service(self, service_name: str) -> None:
        """Stop a single service"""
        try:
            service_info = self.services[service_name]
            
            if service_info.state == ServiceState.STOPPED:
                return
            
            self.logger.info(f"Stopping service: {service_name}")
            service_info.state = ServiceState.STOPPING
            
            # Stop the service
            if hasattr(service_info.instance, 'stop'):
                await service_info.instance.stop()
            
            service_info.state = ServiceState.STOPPED
            self.logger.info(f"Service {service_name} stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping service {service_name}: {e}")
            self.services[service_name].state = ServiceState.ERROR
    
    async def _health_monitoring_loop(self) -> None:
        """Monitor health of all services"""
        while not self.shutdown_event.is_set():
            try:
                await self._check_service_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(5)
    
    async def _check_service_health(self) -> None:
        """Check health of all running services"""
        import time
        current_time = time.time()
        
        for name, service_info in self.services.items():
            if service_info.state != ServiceState.RUNNING:
                continue
            
            try:
                # Check if service has health check method
                if hasattr(service_info.instance, 'health_check'):
                    healthy = await service_info.instance.health_check()
                    if not healthy:
                        self.logger.warning(f"Service {name} failed health check")
                        service_info.error_count += 1
                        
                        # Restart if too many failures
                        if service_info.error_count >= 3:
                            self.logger.error(f"Service {name} has too many health check failures, restarting")
                            asyncio.create_task(self.restart_service(name))
                    else:
                        service_info.error_count = 0
                
                service_info.last_health_check = current_time
                
            except Exception as e:
                self.logger.error(f"Health check failed for service {name}: {e}")
                service_info.error_count += 1