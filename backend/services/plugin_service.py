"""
Plugin System for extensibility
"""

import asyncio
import logging
import importlib
import inspect
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class PluginInterface(ABC):
    """Base interface for all plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description"""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Cleanup plugin resources"""
        pass
    
    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin action"""
        pass

class PluginManager:
    """Plugin manager for loading and managing plugins"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_configs: Dict[str, Dict] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        
    async def start(self):
        """Start the plugin manager"""
        try:
            # Create plugins directory
            plugins_dir = self.config.get_data_path("plugins")
            plugins_dir.mkdir(parents=True, exist_ok=True)
            
            # Load plugin configurations
            await self._load_plugin_configs()
            
            # Load and initialize plugins
            await self._load_plugins()
            
            self.logger.info(f"Plugin Manager started with {len(self.plugins)} plugins")
            
        except Exception as e:
            self.logger.error(f"Failed to start Plugin Manager: {e}")
            raise
    
    async def stop(self):
        """Stop the plugin manager"""
        # Cleanup all plugins
        for plugin in self.plugins.values():
            try:
                await plugin.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up plugin {plugin.name}: {e}")
        
        self.plugins.clear()
        self.hooks.clear()
        self.logger.info("Plugin Manager stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            plugin_statuses = {}
            for name, plugin in self.plugins.items():
                try:
                    plugin_statuses[name] = {
                        "version": plugin.version,
                        "description": plugin.description,
                        "status": "active"
                    }
                except Exception as e:
                    plugin_statuses[name] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            return ComponentStatus(
                name="plugin_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "loaded_plugins": len(self.plugins),
                    "registered_hooks": len(self.hooks),
                    "plugins": plugin_statuses
                }
            )
                
        except Exception as e:
            return ComponentStatus(
                name="plugin_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def _load_plugin_configs(self):
        """Load plugin configurations"""
        config_file = self.config.get_data_path("plugins", "plugins.json")
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    self.plugin_configs = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load plugin configs: {e}")
                self.plugin_configs = {}
        else:
            # Create default config
            self.plugin_configs = {
                "example_plugin": {
                    "enabled": False,
                    "module": "plugins.example_plugin",
                    "class": "ExamplePlugin",
                    "config": {}
                }
            }
            await self._save_plugin_configs()
    
    async def _save_plugin_configs(self):
        """Save plugin configurations"""
        config_file = self.config.get_data_path("plugins", "plugins.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'w') as f:
                json.dump(self.plugin_configs, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save plugin configs: {e}")
    
    async def _load_plugins(self):
        """Load and initialize plugins"""
        plugins_dir = self.config.get_data_path("plugins")
        
        for plugin_name, plugin_config in self.plugin_configs.items():
            if not plugin_config.get("enabled", False):
                continue
            
            try:
                # Import plugin module
                module_name = plugin_config.get("module")
                class_name = plugin_config.get("class")
                
                if not module_name or not class_name:
                    self.logger.warning(f"Invalid config for plugin {plugin_name}")
                    continue
                
                # Try to import from plugins directory first
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        plugins_dir / f"{plugin_name}.py"
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                except:
                    # Fallback to regular import
                    module = importlib.import_module(module_name)
                
                # Get plugin class
                plugin_class = getattr(module, class_name)
                
                # Verify it implements the interface
                if not issubclass(plugin_class, PluginInterface):
                    self.logger.error(f"Plugin {plugin_name} does not implement PluginInterface")
                    continue
                
                # Create and initialize plugin
                plugin = plugin_class()
                
                if await plugin.initialize(plugin_config.get("config", {})):
                    self.plugins[plugin_name] = plugin
                    self.logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
                else:
                    self.logger.error(f"Failed to initialize plugin {plugin_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to load plugin {plugin_name}: {e}")
    
    async def execute_plugin(self, plugin_name: str, action: str, 
                           parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plugin action"""
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin {plugin_name} not found")
        
        try:
            return await self.plugins[plugin_name].execute(action, parameters)
        except Exception as e:
            self.logger.error(f"Error executing plugin {plugin_name}: {e}")
            raise
    
    def register_hook(self, event: str, callback: Callable):
        """Register a hook for an event"""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)
    
    def unregister_hook(self, event: str, callback: Callable):
        """Unregister a hook"""
        if event in self.hooks and callback in self.hooks[event]:
            self.hooks[event].remove(callback)
    
    async def trigger_hook(self, event: str, data: Any = None) -> List[Any]:
        """Trigger all hooks for an event"""
        results = []
        
        if event in self.hooks:
            for callback in self.hooks[event]:
                try:
                    if inspect.iscoroutinefunction(callback):
                        result = await callback(data)
                    else:
                        result = callback(data)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error in hook callback: {e}")
        
        return results
    
    async def install_plugin(self, plugin_path: Path, config: Dict = None):
        """Install a new plugin"""
        try:
            plugins_dir = self.config.get_data_path("plugins")
            
            # Copy plugin file
            plugin_name = plugin_path.stem
            target_path = plugins_dir / f"{plugin_name}.py"
            
            import shutil
            shutil.copy2(plugin_path, target_path)
            
            # Add to config
            self.plugin_configs[plugin_name] = {
                "enabled": True,
                "module": f"plugins.{plugin_name}",
                "class": config.get("class", "Plugin"),
                "config": config.get("config", {})
            }
            
            await self._save_plugin_configs()
            
            # Try to load the plugin
            await self._load_plugins()
            
            self.logger.info(f"Installed plugin: {plugin_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to install plugin: {e}")
            raise
    
    async def uninstall_plugin(self, plugin_name: str):
        """Uninstall a plugin"""
        try:
            # Cleanup plugin if loaded
            if plugin_name in self.plugins:
                await self.plugins[plugin_name].cleanup()
                del self.plugins[plugin_name]
            
            # Remove from config
            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]
                await self._save_plugin_configs()
            
            # Remove plugin file
            plugins_dir = self.config.get_data_path("plugins")
            plugin_file = plugins_dir / f"{plugin_name}.py"
            if plugin_file.exists():
                plugin_file.unlink()
            
            self.logger.info(f"Uninstalled plugin: {plugin_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to uninstall plugin: {e}")
            raise
    
    def list_plugins(self) -> Dict[str, Dict]:
        """List all available plugins"""
        result = {}
        
        for name, config in self.plugin_configs.items():
            plugin_info = {
                "enabled": config.get("enabled", False),
                "config": config.get("config", {}),
                "loaded": name in self.plugins
            }
            
            if name in self.plugins:
                plugin = self.plugins[name]
                plugin_info.update({
                    "name": plugin.name,
                    "version": plugin.version,
                    "description": plugin.description
                })
            
            result[name] = plugin_info
        
        return result

class PluginService:
    """Main plugin service"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.manager = PluginManager(config)
    
    async def start(self):
        """Start the plugin service"""
        await self.manager.start()
        self.logger.info("Plugin Service started")
    
    async def stop(self):
        """Stop the plugin service"""
        await self.manager.stop()
        self.logger.info("Plugin Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        return await self.manager.get_status()
    
    # Delegate methods to manager
    async def execute_plugin(self, plugin_name: str, action: str, parameters: Dict[str, Any]):
        return await self.manager.execute_plugin(plugin_name, action, parameters)
    
    def register_hook(self, event: str, callback: Callable):
        return self.manager.register_hook(event, callback)
    
    async def trigger_hook(self, event: str, data: Any = None):
        return await self.manager.trigger_hook(event, data)
    
    def list_plugins(self):
        return self.manager.list_plugins()