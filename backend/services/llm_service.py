"""
LLM Service for AI Assistant using Ollama
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
import httpx
import aiohttp
from datetime import datetime
import re

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class LLMResponse:
    """Response from LLM processing"""
    def __init__(self, text: str, context_id: str, requires_automation: bool = False,
                 automation_task: Optional[Dict] = None, suggestions: List = None):
        self.text = text
        self.context_id = context_id
        self.requires_automation = requires_automation
        self.automation_task = automation_task or {}
        self.suggestions = suggestions or []
        self.automation_result = None

class LLMService:
    """Service for LLM operations using Ollama"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.ollama_url = "http://localhost:11434"
        self.model = config.models.llm_model
        self.contexts: Dict[str, List[Dict]] = {}
        self.system_prompt = self._build_system_prompt()
        
    async def start(self):
        """Start the LLM service"""
        try:
            # Check if Ollama is running
            await self._check_ollama_status()
            
            # Pull model if not available
            await self._ensure_model_available()
            
            self.logger.info(f"LLM Service started with model: {self.model}")
            
        except Exception as e:
            self.logger.error(f"Failed to start LLM service: {e}")
            # Don't raise in production - allow service to start in degraded mode
            # raise
    
    async def stop(self):
        """Stop the LLM service"""
        self.logger.info("LLM Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_available = any(m['name'] == self.model for m in models)
                    
                    return ComponentStatus(
                        name="llm_service",
                        status=ServiceStatus.HEALTHY if model_available else ServiceStatus.DEGRADED,
                        version=self.model,
                        details={
                            "model": self.model,
                            "available_models": [m['name'] for m in models],
                            "active_contexts": len(self.contexts)
                        }
                    )
                else:
                    return ComponentStatus(
                        name="llm_service",
                        status=ServiceStatus.UNHEALTHY,
                        error="Ollama API not responding"
                    )
                    
        except Exception as e:
            return ComponentStatus(
                name="llm_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def process_message(self, message: str, context_id: Optional[str] = None) -> LLMResponse:
        """Process user message and generate response"""
        try:
            # Generate context ID if not provided
            if not context_id:
                context_id = str(uuid.uuid4())
            
            # Get or create conversation context
            if context_id not in self.contexts:
                self.contexts[context_id] = []
            
            context = self.contexts[context_id]
            
            # Add user message to context
            context.append({"role": "user", "content": message})
            
            # Prepare messages for Ollama
            messages = [{"role": "system", "content": self.system_prompt}] + context
            
            # Generate response
            response_text = await self._generate_response(messages)
            
            # Parse response for automation commands
            automation_task, clean_response = self._parse_automation_commands(response_text)
            
            # Add assistant response to context
            context.append({"role": "assistant", "content": clean_response})
            
            # Limit context size
            if len(context) > 20:
                context = context[-20:]
                self.contexts[context_id] = context
            
            # Generate suggestions
            suggestions = await self._generate_suggestions(message, clean_response)
            
            return LLMResponse(
                text=clean_response,
                context_id=context_id,
                requires_automation=automation_task is not None,
                automation_task=automation_task,
                suggestions=suggestions
            )
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return LLMResponse(
                text="I apologize, but I encountered an error processing your request. Please try again.",
                context_id=context_id or str(uuid.uuid4())
            )
    
    async def _check_ollama_status(self):
        """Check if Ollama is running"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=5.0)
                if response.status_code != 200:
                    raise Exception("Ollama not responding")
        except Exception as e:
            self.logger.error(f"Ollama not available: {e}")
            raise Exception("Ollama service is not running. Please start Ollama first.")
    
    async def _ensure_model_available(self):
        """Ensure the specified model is available"""
        try:
            async with httpx.AsyncClient() as client:
                # Check if model exists
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m['name'] for m in models]
                    
                    if self.model not in model_names:
                        self.logger.info(f"Pulling model: {self.model}")
                        # Pull the model
                        pull_response = await client.post(
                            f"{self.ollama_url}/api/pull",
                            json={"name": self.model},
                            timeout=300.0  # 5 minutes timeout for model download
                        )
                        if pull_response.status_code != 200:
                            raise Exception(f"Failed to pull model: {self.model}")
                        
                        self.logger.info(f"Model {self.model} pulled successfully")
                    else:
                        self.logger.info(f"Model {self.model} already available")
                        
        except Exception as e:
            self.logger.error(f"Error ensuring model availability: {e}")
            raise
    
    async def _generate_response(self, messages: List[Dict]) -> str:
        """Generate response from Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['message']['content']
                else:
                    raise Exception(f"Ollama API error: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            raise
    
    def _parse_automation_commands(self, response: str) -> tuple[Optional[Dict], str]:
        """Parse automation commands from response"""
        # Look for automation commands in the format: [AUTOMATION:type:parameters]
        automation_pattern = r'\[AUTOMATION:([^:]+):([^\]]+)\]'
        matches = re.findall(automation_pattern, response)
        
        if matches:
            # Take the first automation command
            task_type, parameters_str = matches[0]
            
            try:
                # Parse parameters as JSON
                parameters = json.loads(parameters_str)
                
                automation_task = {
                    "task_id": str(uuid.uuid4()),
                    "task_type": task_type,
                    "parameters": parameters,
                    "priority": 1,
                    "timeout": 300
                }
                
                # Remove automation commands from response
                clean_response = re.sub(automation_pattern, '', response).strip()
                
                return automation_task, clean_response
                
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse automation parameters: {parameters_str}")
        
        return None, response
    
    async def _generate_suggestions(self, user_message: str, response: str) -> List[Dict]:
        """Generate proactive suggestions"""
        suggestions = []
        
        # Simple rule-based suggestions for now
        # In production, this could use a separate model or more sophisticated logic
        
        if "file" in user_message.lower() or "document" in user_message.lower():
            suggestions.append({
                "id": str(uuid.uuid4()),
                "text": "Would you like me to help organize your files?",
                "action": "organize_files",
                "confidence": 0.7
            })
        
        if "email" in user_message.lower():
            suggestions.append({
                "id": str(uuid.uuid4()),
                "text": "I can help you draft or send emails automatically",
                "action": "email_automation",
                "confidence": 0.8
            })
        
        if "schedule" in user_message.lower() or "calendar" in user_message.lower():
            suggestions.append({
                "id": str(uuid.uuid4()),
                "text": "I can help manage your calendar and schedule meetings",
                "action": "calendar_management",
                "confidence": 0.9
            })
        
        return suggestions
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the AI assistant"""
        return """You are an AI Assistant that acts as a personal AI employee. You help users with various tasks including:

1. Application control and automation
2. File and document management
3. Web browsing and research
4. Creative tasks like image and video generation
5. Office automation (Excel, Word, PowerPoint, etc.)
6. Email and communication management
7. System administration tasks

Key capabilities:
- You can control applications on the user's computer
- You can automate repetitive tasks
- You can generate images, documents, and other content
- You can browse the web and gather information
- You can learn from user patterns and suggest improvements

When you need to perform automation tasks, use the format:
[AUTOMATION:task_type:{"parameter": "value"}]

Available automation types:
- app_control: Open, close, or control applications
- file_operations: Create, move, copy, delete files
- web_automation: Browse websites, fill forms, extract data
- document_creation: Create documents, presentations, spreadsheets
- image_generation: Generate images using AI models
- system_tasks: System administration and configuration

Always be helpful, proactive, and suggest ways to improve the user's workflow. If you notice repetitive tasks, offer to automate them. Be conversational and friendly while maintaining professionalism.

Remember: You are always running in the background and can provide proactive assistance. Focus on completing full end-to-end workflows rather than partial solutions."""
    
    def clear_context(self, context_id: str):
        """Clear conversation context"""
        if context_id in self.contexts:
            del self.contexts[context_id]
    
    def get_context_summary(self, context_id: str) -> Optional[str]:
        """Get summary of conversation context"""
        if context_id not in self.contexts:
            return None
        
        context = self.contexts[context_id]
        if not context:
            return None
        
        # Simple summary - in production, could use summarization model
        messages = [msg['content'] for msg in context[-5:]]  # Last 5 messages
        return " | ".join(messages)