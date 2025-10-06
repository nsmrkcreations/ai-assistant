"""
Example Plugin for AI Assistant
"""

from typing import Dict, Any
from backend.services.plugin_service import PluginInterface

class ExamplePlugin(PluginInterface):
    """Example plugin implementation"""
    
    @property
    def name(self) -> str:
        return "Example Plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "An example plugin demonstrating the plugin system"
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin"""
        self.config = config
        self.greeting = config.get("greeting", "Hello from Example Plugin!")
        return True
    
    async def cleanup(self):
        """Cleanup plugin resources"""
        pass
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin action"""
        if action == "greet":
            name = parameters.get("name", "World")
            return {
                "success": True,
                "message": f"{self.greeting} Hello, {name}!"
            }
        elif action == "echo":
            message = parameters.get("message", "")
            return {
                "success": True,
                "echo": message
            }
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }