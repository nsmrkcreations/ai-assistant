"""
Task Orchestrator Service for AI Assistant
Manages complex multi-step workflows and task dependencies
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import networkx as nx

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Task:
    """Represents a single task in a workflow"""
    task_id: str
    name: str
    description: str
    task_type: str
    parameters: Dict[str, Any]
    dependencies: List[str]
    priority: TaskPriority
    timeout: float
    retry_count: int
    max_retries: int
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None@datacla
ss
class Workflow:
    """Represents a complete workflow"""
    workflow_id: str
    name: str
    description: str
    tasks: Dict[str, Task]
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    metadata: Dict[str, Any] = None

class TaskOrchestratorService:
    """Service for orchestrating complex multi-step workflows"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Workflow management
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_history: List[Dict[str, Any]] = []
        self.task_executors: Dict[str, Callable] = {}
        
        # Execution control
        self.max_concurrent_tasks = 5
        self.running_tasks: Set[str] = set()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        
        # Templates and patterns
        self.workflow_templates: Dict[str, Dict[str, Any]] = {}
        
        # Initialize built-in task executors
        self._initialize_task_executors()
        self._initialize_workflow_templates()
        
    async def start(self):
        """Start the task orchestrator service"""
        try:
            # Start task execution workers
            for i in range(self.max_concurrent_tasks):
                asyncio.create_task(self._task_execution_worker(f"worker_{i}"))
            
            # Start workflow monitoring
            asyncio.create_task(self._workflow_monitoring_loop())
            
            self.logger.info("Task Orchestrator Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start task orchestrator service: {e}")
            raise
    
    async def stop(self):
        """Stop the task orchestrator service"""
        # Cancel all active workflows
        for workflow_id in list(self.active_workflows.keys()):
            await self.cancel_workflow(workflow_id)
        
        self.logger.info("Task Orchestrator Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="task_orchestrator_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "active_workflows": len(self.active_workflows),
                    "running_tasks": len(self.running_tasks),
                    "queued_tasks": self.task_queue.qsize(),
                    "workflow_templates": len(self.workflow_templates),
                    "task_executors": len(self.task_executors)
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="task_orchestrator_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def create_workflow(self, workflow_spec: Dict[str, Any]) -> str:
        """Create a new workflow from specification"""
        try:
            workflow_id = str(uuid.uuid4())
            
            # Parse workflow specification
            workflow = Workflow(
                workflow_id=workflow_id,
                name=workflow_spec.get('name', 'Untitled Workflow'),
                description=workflow_spec.get('description', ''),
                tasks={},
                created_at=time.time(),
                metadata=workflow_spec.get('metadata', {})
            )
            
            # Create tasks
            for task_spec in workflow_spec.get('tasks', []):
                task = Task(
                    task_id=task_spec['task_id'],
                    name=task_spec.get('name', task_spec['task_id']),
                    description=task_spec.get('description', ''),
                    task_type=task_spec['type'],
                    parameters=task_spec.get('parameters', {}),
                    dependencies=task_spec.get('dependencies', []),
                    priority=TaskPriority(task_spec.get('priority', 2)),
                    timeout=task_spec.get('timeout', 300),
                    retry_count=0,
                    max_retries=task_spec.get('max_retries', 3),
                    status=TaskStatus.PENDING,
                    created_at=time.time()
                )
                
                workflow.tasks[task.task_id] = task
            
            # Validate workflow
            if not await self._validate_workflow(workflow):
                raise Exception("Workflow validation failed")
            
            # Store workflow
            self.active_workflows[workflow_id] = workflow
            
            self.logger.info(f"Created workflow: {workflow.name} ({workflow_id})")
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Error creating workflow: {e}")
            raise
    
    async def start_workflow(self, workflow_id: str) -> bool:
        """Start executing a workflow"""
        try:
            if workflow_id not in self.active_workflows:
                raise Exception(f"Workflow {workflow_id} not found")
            
            workflow = self.active_workflows[workflow_id]
            
            if workflow.status != TaskStatus.PENDING:
                raise Exception(f"Workflow {workflow_id} is not in pending state")
            
            workflow.status = TaskStatus.RUNNING
            workflow.started_at = time.time()
            
            # Queue initial tasks (those with no dependencies)
            initial_tasks = [
                task for task in workflow.tasks.values()
                if not task.dependencies
            ]
            
            for task in initial_tasks:
                await self._queue_task(workflow_id, task.task_id)
            
            self.logger.info(f"Started workflow: {workflow.name} ({workflow_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting workflow: {e}")
            return False
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        try:
            if workflow_id not in self.active_workflows:
                return False
            
            workflow = self.active_workflows[workflow_id]
            workflow.status = TaskStatus.CANCELLED
            
            # Cancel all pending and running tasks
            for task in workflow.tasks.values():
                if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    task.status = TaskStatus.CANCELLED
            
            # Remove from active workflows
            self._archive_workflow(workflow)
            del self.active_workflows[workflow_id]
            
            self.logger.info(f"Cancelled workflow: {workflow.name} ({workflow_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling workflow: {e}")
            return False
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status and progress"""
        if workflow_id not in self.active_workflows:
            return None
        
        workflow = self.active_workflows[workflow_id]
        
        # Calculate progress
        total_tasks = len(workflow.tasks)
        completed_tasks = len([t for t in workflow.tasks.values() if t.status == TaskStatus.COMPLETED])
        progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        workflow.progress = progress
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "progress": progress,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "running_tasks": len([t for t in workflow.tasks.values() if t.status == TaskStatus.RUNNING]),
            "failed_tasks": len([t for t in workflow.tasks.values() if t.status == TaskStatus.FAILED]),
            "created_at": workflow.created_at,
            "started_at": workflow.started_at,
            "completed_at": workflow.completed_at,
            "tasks": {
                task_id: {
                    "name": task.name,
                    "status": task.status.value,
                    "progress": self._calculate_task_progress(task),
                    "error": task.error
                }
                for task_id, task in workflow.tasks.items()
            }
        }
    
    async def create_workflow_from_template(self, template_name: str, 
                                          parameters: Dict[str, Any]) -> str:
        """Create workflow from a template"""
        try:
            if template_name not in self.workflow_templates:
                raise Exception(f"Template {template_name} not found")
            
            template = self.workflow_templates[template_name]
            
            # Substitute parameters in template
            workflow_spec = self._substitute_template_parameters(template, parameters)
            
            # Create workflow
            return await self.create_workflow(workflow_spec)
            
        except Exception as e:
            self.logger.error(f"Error creating workflow from template: {e}")
            raise
    
    async def _task_execution_worker(self, worker_id: str):
        """Worker that executes tasks from the queue"""
        while True:
            try:
                # Get task from queue
                workflow_id, task_id = await self.task_queue.get()
                
                if workflow_id not in self.active_workflows:
                    continue
                
                workflow = self.active_workflows[workflow_id]
                task = workflow.tasks.get(task_id)
                
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                # Execute task
                await self._execute_task(workflow_id, task_id)
                
                # Check if workflow is complete
                await self._check_workflow_completion(workflow_id)
                
            except Exception as e:
                self.logger.error(f"Error in task execution worker {worker_id}: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, workflow_id: str, task_id: str):
        """Execute a single task"""
        try:
            workflow = self.active_workflows[workflow_id]
            task = workflow.tasks[task_id]
            
            # Mark task as running
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            self.running_tasks.add(task_id)
            
            self.logger.info(f"Executing task: {task.name} ({task_id})")
            
            # Get task executor
            executor = self.task_executors.get(task.task_type)
            if not executor:
                raise Exception(f"No executor found for task type: {task.task_type}")
            
            # Execute task with timeout
            try:
                result = await asyncio.wait_for(
                    executor(task.parameters),
                    timeout=task.timeout
                )
                
                # Task completed successfully
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.result = result
                
                self.logger.info(f"Task completed: {task.name} ({task_id})")
                
                # Queue dependent tasks
                await self._queue_dependent_tasks(workflow_id, task_id)
                
            except asyncio.TimeoutError:
                raise Exception(f"Task timeout after {task.timeout} seconds")
            
        except Exception as e:
            # Task failed
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.error = str(e)
            task.retry_count += 1
            
            self.logger.error(f"Task failed: {task.name} ({task_id}) - {e}")
            
            # Retry if possible
            if task.retry_count <= task.max_retries:
                self.logger.info(f"Retrying task: {task.name} (attempt {task.retry_count})")
                task.status = TaskStatus.PENDING
                await self._queue_task(workflow_id, task_id)
            else:
                self.logger.error(f"Task failed permanently: {task.name} ({task_id})")
                # Mark workflow as failed if critical task fails
                if task.priority == TaskPriority.CRITICAL:
                    workflow.status = TaskStatus.FAILED
        
        finally:
            self.running_tasks.discard(task_id)
    
    async def _queue_task(self, workflow_id: str, task_id: str):
        """Queue a task for execution"""
        await self.task_queue.put((workflow_id, task_id))
    
    async def _queue_dependent_tasks(self, workflow_id: str, completed_task_id: str):
        """Queue tasks that depend on the completed task"""
        workflow = self.active_workflows[workflow_id]
        
        for task in workflow.tasks.values():
            if (task.status == TaskStatus.PENDING and 
                completed_task_id in task.dependencies):
                
                # Check if all dependencies are completed
                all_deps_completed = all(
                    workflow.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                    if dep_id in workflow.tasks
                )
                
                if all_deps_completed:
                    await self._queue_task(workflow_id, task.task_id)
    
    async def _check_workflow_completion(self, workflow_id: str):
        """Check if workflow is complete"""
        workflow = self.active_workflows[workflow_id]
        
        # Count task statuses
        pending_tasks = [t for t in workflow.tasks.values() if t.status == TaskStatus.PENDING]
        running_tasks = [t for t in workflow.tasks.values() if t.status == TaskStatus.RUNNING]
        failed_tasks = [t for t in workflow.tasks.values() if t.status == TaskStatus.FAILED]
        
        # Check completion conditions
        if not pending_tasks and not running_tasks:
            if failed_tasks:
                workflow.status = TaskStatus.FAILED
            else:
                workflow.status = TaskStatus.COMPLETED
            
            workflow.completed_at = time.time()
            
            self.logger.info(f"Workflow completed: {workflow.name} ({workflow_id}) - {workflow.status.value}")
            
            # Archive completed workflow
            self._archive_workflow(workflow)
            del self.active_workflows[workflow_id]
    
    async def _validate_workflow(self, workflow: Workflow) -> bool:
        """Validate workflow structure and dependencies"""
        try:
            # Check for circular dependencies
            graph = nx.DiGraph()
            
            for task in workflow.tasks.values():
                graph.add_node(task.task_id)
                for dep in task.dependencies:
                    if dep in workflow.tasks:
                        graph.add_edge(dep, task.task_id)
            
            if not nx.is_directed_acyclic_graph(graph):
                self.logger.error("Workflow contains circular dependencies")
                return False
            
            # Check that all dependencies exist
            for task in workflow.tasks.values():
                for dep in task.dependencies:
                    if dep not in workflow.tasks:
                        self.logger.error(f"Task {task.task_id} depends on non-existent task {dep}")
                        return False
            
            # Check that task executors exist
            for task in workflow.tasks.values():
                if task.task_type not in self.task_executors:
                    self.logger.error(f"No executor for task type: {task.task_type}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Workflow validation error: {e}")
            return False
    
    def _calculate_task_progress(self, task: Task) -> float:
        """Calculate task progress percentage"""
        if task.status == TaskStatus.COMPLETED:
            return 100.0
        elif task.status == TaskStatus.RUNNING:
            # Estimate progress based on elapsed time vs timeout
            if task.started_at:
                elapsed = time.time() - task.started_at
                return min(90.0, (elapsed / task.timeout) * 100)
        elif task.status == TaskStatus.FAILED:
            return 0.0
        
        return 0.0
    
    def _archive_workflow(self, workflow: Workflow):
        """Archive completed workflow"""
        archive_entry = {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "created_at": workflow.created_at,
            "started_at": workflow.started_at,
            "completed_at": workflow.completed_at,
            "progress": workflow.progress,
            "task_count": len(workflow.tasks),
            "metadata": workflow.metadata
        }
        
        self.workflow_history.append(archive_entry)
        
        # Keep history manageable
        if len(self.workflow_history) > 100:
            self.workflow_history = self.workflow_history[-50:]
    
    async def _workflow_monitoring_loop(self):
        """Monitor workflows for timeouts and issues"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = time.time()
                
                for workflow in list(self.active_workflows.values()):
                    # Check for stuck workflows
                    if (workflow.status == TaskStatus.RUNNING and 
                        workflow.started_at and 
                        current_time - workflow.started_at > 3600):  # 1 hour timeout
                        
                        self.logger.warning(f"Workflow timeout: {workflow.name}")
                        await self.cancel_workflow(workflow.workflow_id)
                
            except Exception as e:
                self.logger.error(f"Error in workflow monitoring: {e}")
    
    def _initialize_task_executors(self):
        """Initialize built-in task executors"""
        
        # LLM task executor
        async def llm_task_executor(parameters: Dict[str, Any]) -> Dict[str, Any]:
            # This would integrate with the LLM service
            prompt = parameters.get('prompt', '')
            context = parameters.get('context', {})
            
            # Simulate LLM processing
            await asyncio.sleep(2)
            
            return {
                'response': f'AI response to: {prompt}',
                'context': context
            }
        
        # File operation executor
        async def file_operation_executor(parameters: Dict[str, Any]) -> Dict[str, Any]:
            operation = parameters.get('operation')
            file_path = parameters.get('file_path')
            content = parameters.get('content', '')
            
            if operation == 'create':
                Path(file_path).write_text(content)
                return {'status': 'created', 'file_path': file_path}
            elif operation == 'read':
                content = Path(file_path).read_text()
                return {'status': 'read', 'content': content}
            
            return {'status': 'unknown_operation'}
        
        # Web automation executor
        async def web_automation_executor(parameters: Dict[str, Any]) -> Dict[str, Any]:
            # This would integrate with the web automation service
            action = parameters.get('action')
            url = parameters.get('url')
            
            await asyncio.sleep(3)  # Simulate web operation
            
            return {
                'action': action,
                'url': url,
                'status': 'completed'
            }
        
        # Image generation executor
        async def image_generation_executor(parameters: Dict[str, Any]) -> Dict[str, Any]:
            # This would integrate with the asset generation service
            prompt = parameters.get('prompt')
            style = parameters.get('style', 'realistic')
            
            await asyncio.sleep(5)  # Simulate image generation
            
            return {
                'prompt': prompt,
                'style': style,
                'image_path': f'/generated/image_{int(time.time())}.png',
                'status': 'generated'
            }
        
        # Register executors
        self.task_executors = {
            'llm_task': llm_task_executor,
            'file_operation': file_operation_executor,
            'web_automation': web_automation_executor,
            'image_generation': image_generation_executor
        }
    
    def _initialize_workflow_templates(self):
        """Initialize workflow templates"""
        
        # Content creation workflow
        content_creation_template = {
            'name': 'Content Creation Workflow',
            'description': 'Create comprehensive content with research, writing, and media generation',
            'tasks': [
                {
                    'task_id': 'research',
                    'name': 'Research Topic',
                    'type': 'web_automation',
                    'parameters': {
                        'action': 'research',
                        'topic': '{{topic}}',
                        'sources': 5
                    },
                    'dependencies': [],
                    'priority': 2,
                    'timeout': 300
                },
                {
                    'task_id': 'outline',
                    'name': 'Create Outline',
                    'type': 'llm_task',
                    'parameters': {
                        'prompt': 'Create an outline for {{content_type}} about {{topic}}',
                        'context': {'research_data': '{{research.result}}'}
                    },
                    'dependencies': ['research'],
                    'priority': 2,
                    'timeout': 120
                },
                {
                    'task_id': 'write_content',
                    'name': 'Write Content',
                    'type': 'llm_task',
                    'parameters': {
                        'prompt': 'Write {{content_type}} based on outline',
                        'context': {'outline': '{{outline.result}}'}
                    },
                    'dependencies': ['outline'],
                    'priority': 2,
                    'timeout': 300
                },
                {
                    'task_id': 'generate_images',
                    'name': 'Generate Supporting Images',
                    'type': 'image_generation',
                    'parameters': {
                        'prompt': 'Create image for {{topic}}',
                        'style': '{{image_style}}'
                    },
                    'dependencies': ['outline'],
                    'priority': 1,
                    'timeout': 600
                },
                {
                    'task_id': 'save_content',
                    'name': 'Save Final Content',
                    'type': 'file_operation',
                    'parameters': {
                        'operation': 'create',
                        'file_path': '{{output_file}}',
                        'content': '{{write_content.result}}'
                    },
                    'dependencies': ['write_content', 'generate_images'],
                    'priority': 2,
                    'timeout': 60
                }
            ]
        }
        
        # Document processing workflow
        document_processing_template = {
            'name': 'Document Processing Workflow',
            'description': 'Process and analyze documents with AI',
            'tasks': [
                {
                    'task_id': 'read_document',
                    'name': 'Read Document',
                    'type': 'file_operation',
                    'parameters': {
                        'operation': 'read',
                        'file_path': '{{input_file}}'
                    },
                    'dependencies': [],
                    'priority': 3,
                    'timeout': 60
                },
                {
                    'task_id': 'analyze_content',
                    'name': 'Analyze Content',
                    'type': 'llm_task',
                    'parameters': {
                        'prompt': 'Analyze this document: {{read_document.result.content}}',
                        'context': {'analysis_type': '{{analysis_type}}'}
                    },
                    'dependencies': ['read_document'],
                    'priority': 2,
                    'timeout': 180
                },
                {
                    'task_id': 'generate_summary',
                    'name': 'Generate Summary',
                    'type': 'llm_task',
                    'parameters': {
                        'prompt': 'Create summary based on analysis',
                        'context': {'analysis': '{{analyze_content.result}}'}
                    },
                    'dependencies': ['analyze_content'],
                    'priority': 2,
                    'timeout': 120
                },
                {
                    'task_id': 'save_results',
                    'name': 'Save Analysis Results',
                    'type': 'file_operation',
                    'parameters': {
                        'operation': 'create',
                        'file_path': '{{output_file}}',
                        'content': '{{generate_summary.result}}'
                    },
                    'dependencies': ['generate_summary'],
                    'priority': 2,
                    'timeout': 60
                }
            ]
        }
        
        self.workflow_templates = {
            'content_creation': content_creation_template,
            'document_processing': document_processing_template
        }
    
    def _substitute_template_parameters(self, template: Dict[str, Any], 
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute parameters in workflow template"""
        import re
        
        def substitute_value(value):
            if isinstance(value, str):
                # Replace {{parameter}} with actual values
                for param_name, param_value in parameters.items():
                    pattern = f'{{{{{param_name}}}}}'
                    value = value.replace(pattern, str(param_value))
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(template)
    
    def get_workflow_templates(self) -> List[Dict[str, Any]]:
        """Get available workflow templates"""
        return [
            {
                'name': template_name,
                'description': template['description'],
                'task_count': len(template['tasks'])
            }
            for template_name, template in self.workflow_templates.items()
        ]
    
    def get_workflow_history(self) -> List[Dict[str, Any]]:
        """Get workflow execution history"""
        return self.workflow_history.copy()
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get orchestrator service statistics"""
        return {
            "active_workflows": len(self.active_workflows),
            "running_tasks": len(self.running_tasks),
            "queued_tasks": self.task_queue.qsize(),
            "workflow_templates": len(self.workflow_templates),
            "task_executors": len(self.task_executors),
            "workflow_history_count": len(self.workflow_history),
            "max_concurrent_tasks": self.max_concurrent_tasks
        }