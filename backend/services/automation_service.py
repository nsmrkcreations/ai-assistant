"""
Automation Service for controlling applications and performing GUI automation
"""

import asyncio
import logging
import subprocess
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os
import platform

# GUI automation imports
try:
    import pyautogui
    import pygetwindow as gw
    import pyperclip
    from pynput import keyboard, mouse
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

from models.chat_models import ComponentStatus, ServiceStatus, AutomationTask, AutomationResult, TaskStatus
from utils.config import Config

class AutomationService:
    """Service for application control and GUI automation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_tasks: Dict[str, AutomationTask] = {}
        self.task_results: Dict[str, AutomationResult] = {}
        
        # Configure PyAutoGUI safety
        if GUI_AVAILABLE:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        
    async def start(self):
        """Start the automation service"""
        try:
            if not GUI_AVAILABLE:
                self.logger.warning("GUI automation libraries not available - installing dependencies")
                await self._install_gui_dependencies()
            
            # Test basic functionality
            if GUI_AVAILABLE:
                screen_size = pyautogui.size()
                self.logger.info(f"Automation Service started - Screen size: {screen_size}")
            else:
                self.logger.warning("Automation Service started with limited functionality")
            
        except Exception as e:
            self.logger.error(f"Failed to start automation service: {e}")
            # Don't raise - allow graceful degradation
    
    async def stop(self):
        """Stop the automation service"""
        # Cancel any active tasks
        for task_id in list(self.active_tasks.keys()):
            await self.cancel_task(task_id)
        
        self.logger.info("Automation Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            if GUI_AVAILABLE:
                return ComponentStatus(
                    name="automation_service",
                    status=ServiceStatus.HEALTHY,
                    version="1.0.0",
                    details={
                        "gui_available": True,
                        "active_tasks": len(self.active_tasks),
                        "completed_tasks": len(self.task_results),
                        "screen_size": list(pyautogui.size()) if GUI_AVAILABLE else None
                    }
                )
            else:
                return ComponentStatus(
                    name="automation_service",
                    status=ServiceStatus.DEGRADED,
                    error="GUI automation libraries not available"
                )
                
        except Exception as e:
            return ComponentStatus(
                name="automation_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def execute_task(self, task: AutomationTask) -> AutomationResult:
        """Execute an automation task"""
        if not GUI_AVAILABLE:
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error="GUI automation not available"
            )
        
        self.active_tasks[task.task_id] = task
        
        try:
            result = await self._execute_task_internal(task)
            self.task_results[task.task_id] = result
            
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            result = AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(e)
            )
            
            self.task_results[task.task_id] = result
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            return result
    
    async def _execute_task_internal(self, task: AutomationTask) -> AutomationResult:
        """Internal task execution logic"""
        task_type = task.parameters.get('task_type', 'unknown')
        
        if task_type == 'app_control':
            return await self._handle_app_control(task)
        elif task_type == 'mouse_keyboard':
            return await self._handle_mouse_keyboard(task)
        elif task_type == 'window_management':
            return await self._handle_window_management(task)
        elif task_type == 'screenshot':
            return await self._handle_screenshot(task)
        elif task_type == 'text_input':
            return await self._handle_text_input(task)
        else:
            raise Exception(f"Unknown task type: {task_type}")
    
    async def _handle_app_control(self, task: AutomationTask) -> AutomationResult:
        """Handle application control tasks"""
        action = task.parameters.get('action')
        app_name = task.parameters.get('app_name', '')
        
        if action == 'open':
            return await self._open_application(task, app_name)
        elif action == 'close':
            return await self._close_application(task, app_name)
        elif action == 'focus':
            return await self._focus_application(task, app_name)
        else:
            raise Exception(f"Unknown app control action: {action}")
    
    async def _open_application(self, task: AutomationTask, app_name: str) -> AutomationResult:
        """Open an application"""
        try:
            system = platform.system().lower()
            
            if system == 'windows':
                # Try common Windows applications
                app_commands = {
                    'notepad': 'notepad.exe',
                    'calculator': 'calc.exe',
                    'paint': 'mspaint.exe',
                    'wordpad': 'wordpad.exe',
                    'explorer': 'explorer.exe',
                    'cmd': 'cmd.exe',
                    'powershell': 'powershell.exe',
                    'chrome': 'chrome.exe',
                    'firefox': 'firefox.exe',
                    'edge': 'msedge.exe'
                }
                
                command = app_commands.get(app_name.lower(), app_name)
                
            elif system == 'darwin':  # macOS
                app_commands = {
                    'textedit': 'TextEdit',
                    'calculator': 'Calculator',
                    'finder': 'Finder',
                    'terminal': 'Terminal',
                    'safari': 'Safari',
                    'chrome': 'Google Chrome',
                    'firefox': 'Firefox'
                }
                
                app_name_proper = app_commands.get(app_name.lower(), app_name)
                command = f'open -a "{app_name_proper}"'
                
            else:  # Linux
                app_commands = {
                    'gedit': 'gedit',
                    'calculator': 'gnome-calculator',
                    'files': 'nautilus',
                    'terminal': 'gnome-terminal',
                    'firefox': 'firefox',
                    'chrome': 'google-chrome'
                }
                
                command = app_commands.get(app_name.lower(), app_name)
            
            # Execute the command
            if system == 'darwin' and command.startswith('open'):
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
            
            # Wait a moment for the app to start
            await asyncio.sleep(2)
            
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"Application '{app_name}' opened successfully",
                output_data={"command": command, "stdout": stdout.decode(), "stderr": stderr.decode()}
            )
            
        except Exception as e:
            raise Exception(f"Failed to open application '{app_name}': {e}")
    
    async def _close_application(self, task: AutomationTask, app_name: str) -> AutomationResult:
        """Close an application"""
        try:
            # Find windows with the app name
            windows = gw.getWindowsWithTitle(app_name)
            
            if not windows:
                # Try to find by partial match
                all_windows = gw.getAllWindows()
                windows = [w for w in all_windows if app_name.lower() in w.title.lower()]
            
            if windows:
                for window in windows:
                    try:
                        window.close()
                    except:
                        # If close() doesn't work, try to kill the process
                        pass
                
                return AutomationResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    result=f"Closed {len(windows)} window(s) for '{app_name}'"
                )
            else:
                return AutomationResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    result=f"No windows found for '{app_name}'"
                )
                
        except Exception as e:
            raise Exception(f"Failed to close application '{app_name}': {e}")
    
    async def _focus_application(self, task: AutomationTask, app_name: str) -> AutomationResult:
        """Focus an application window"""
        try:
            windows = gw.getWindowsWithTitle(app_name)
            
            if not windows:
                all_windows = gw.getAllWindows()
                windows = [w for w in all_windows if app_name.lower() in w.title.lower()]
            
            if windows:
                window = windows[0]  # Focus the first matching window
                window.activate()
                
                return AutomationResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    result=f"Focused window: {window.title}"
                )
            else:
                raise Exception(f"No window found with title containing '{app_name}'")
                
        except Exception as e:
            raise Exception(f"Failed to focus application '{app_name}': {e}")
    
    async def _handle_mouse_keyboard(self, task: AutomationTask) -> AutomationResult:
        """Handle mouse and keyboard actions"""
        action = task.parameters.get('action')
        
        if action == 'click':
            x = task.parameters.get('x', 0)
            y = task.parameters.get('y', 0)
            button = task.parameters.get('button', 'left')
            clicks = task.parameters.get('clicks', 1)
            
            pyautogui.click(x, y, clicks=clicks, button=button)
            
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"Clicked at ({x}, {y}) with {button} button, {clicks} times"
            )
            
        elif action == 'type':
            text = task.parameters.get('text', '')
            interval = task.parameters.get('interval', 0.01)
            
            pyautogui.typewrite(text, interval=interval)
            
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}"
            )
            
        elif action == 'hotkey':
            keys = task.parameters.get('keys', [])
            
            if isinstance(keys, str):
                keys = keys.split('+')
            
            pyautogui.hotkey(*keys)
            
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"Pressed hotkey: {'+'.join(keys)}"
            )
            
        else:
            raise Exception(f"Unknown mouse/keyboard action: {action}")
    
    async def _handle_window_management(self, task: AutomationTask) -> AutomationResult:
        """Handle window management tasks"""
        action = task.parameters.get('action')
        
        if action == 'list_windows':
            windows = gw.getAllWindows()
            window_list = [{"title": w.title, "left": w.left, "top": w.top, "width": w.width, "height": w.height} 
                          for w in windows if w.title.strip()]
            
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"Found {len(window_list)} windows",
                output_data={"windows": window_list}
            )
            
        else:
            raise Exception(f"Unknown window management action: {action}")
    
    async def _handle_screenshot(self, task: AutomationTask) -> AutomationResult:
        """Handle screenshot tasks"""
        try:
            region = task.parameters.get('region')  # (left, top, width, height)
            
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Save screenshot
            screenshots_dir = self.config.get_data_path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            filename = f"screenshot_{task.task_id}_{int(time.time())}.png"
            filepath = screenshots_dir / filename
            
            screenshot.save(str(filepath))
            
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"Screenshot saved: {filename}",
                output_data={"filepath": str(filepath), "size": screenshot.size}
            )
            
        except Exception as e:
            raise Exception(f"Failed to take screenshot: {e}")
    
    async def _handle_text_input(self, task: AutomationTask) -> AutomationResult:
        """Handle text input and clipboard operations"""
        action = task.parameters.get('action')
        
        if action == 'paste':
            text = task.parameters.get('text', '')
            
            # Copy to clipboard and paste
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            
            return AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"Pasted text: {text[:50]}{'...' if len(text) > 50 else ''}"
            )
            
        elif action == 'copy':
            # Copy current selection
            pyautogui.hotkey('ctrl', 'c')
            await asyncio.sleep(0.1)  # Wait for clipboard
            
            try:
                copied_text = pyperclip.paste()
                return AutomationResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    result="Text copied to clipboard",
                    output_data={"text": copied_text}
                )
            except:
                return AutomationResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    result="Copy command sent (clipboard content unknown)"
                )
                
        else:
            raise Exception(f"Unknown text input action: {action}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an active task"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            
            # Create a cancelled result
            self.task_results[task_id] = AutomationResult(
                task_id=task_id,
                status=TaskStatus.CANCELLED,
                result="Task was cancelled"
            )
            
            return True
        
        return False
    
    async def get_task_result(self, task_id: str) -> Optional[AutomationResult]:
        """Get the result of a completed task"""
        return self.task_results.get(task_id)
    
    async def _install_gui_dependencies(self):
        """Install GUI automation dependencies"""
        try:
            import subprocess
            import sys
            
            packages = ['pyautogui', 'pygetwindow', 'pyperclip', 'pynput']
            
            for package in packages:
                self.logger.info(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            
            # Try to import again
            global GUI_AVAILABLE
            try:
                import pyautogui
                import pygetwindow as gw
                import pyperclip
                from pynput import keyboard, mouse
                GUI_AVAILABLE = True
                self.logger.info("GUI automation dependencies installed successfully")
            except ImportError:
                self.logger.error("Failed to import GUI dependencies after installation")
                
        except Exception as e:
            self.logger.error(f"Failed to install GUI dependencies: {e}")
    
    def get_screen_info(self) -> Dict[str, Any]:
        """Get screen information"""
        if not GUI_AVAILABLE:
            return {"error": "GUI not available"}
        
        try:
            size = pyautogui.size()
            return {
                "width": size.width,
                "height": size.height,
                "position": pyautogui.position()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def stop(self):
        """Stop the automation service"""
        # Cancel any running tasks
        for task_id in list(self.active_tasks.keys()):
            await self.cancel_task(task_id)
        
        self.logger.info("Automation Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="automation_service",
                status=ServiceStatus.HEALTHY if GUI_AVAILABLE else ServiceStatus.DEGRADED,
                details={
                    "gui_available": GUI_AVAILABLE,
                    "active_tasks": len(self.active_tasks),
                    "completed_tasks": len(self.task_results),
                    "platform": platform.system()
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="automation_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def execute_task(self, task_data: Dict[str, Any]) -> AutomationResult:
        """Execute automation task"""
        start_time = time.time()
        
        try:
            # Create task object
            task = AutomationTask(**task_data)
            self.active_tasks[task.task_id] = task
            
            self.logger.info(f"Executing automation task: {task.task_type}")
            
            # Route to appropriate handler
            result_data = None
            if task.task_type == "app_control":
                result_data = await self._handle_app_control(task)
            elif task.task_type == "file_operations":
                result_data = await self._handle_file_operations(task)
            elif task.task_type == "gui_automation":
                result_data = await self._handle_gui_automation(task)
            elif task.task_type == "system_tasks":
                result_data = await self._handle_system_tasks(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            # Create successful result
            result = AutomationResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=result_data,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            result = AutomationResult(
                task_id=task_data.get("task_id", str(uuid.uuid4())),
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time
            )
        
        finally:
            # Clean up
            task_id = task_data.get("task_id")
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            if task_id:
                self.task_results[task_id] = result
        
        return result
    
    async def _handle_app_control(self, task: AutomationTask) -> Dict[str, Any]:
        """Handle application control tasks"""
        action = task.parameters.get("action")
        app_name = task.parameters.get("app_name")
        
        if action == "open":
            return await self._open_application(app_name, task.parameters)
        elif action == "close":
            return await self._close_application(app_name)
        elif action == "focus":
            return await self._focus_application(app_name)
        elif action == "list":
            return await self._list_applications()
        else:
            raise ValueError(f"Unknown app control action: {action}")
    
    async def _handle_file_operations(self, task: AutomationTask) -> Dict[str, Any]:
        """Handle file operation tasks"""
        action = task.parameters.get("action")
        
        if action == "create":
            return await self._create_file(task.parameters)
        elif action == "copy":
            return await self._copy_file(task.parameters)
        elif action == "move":
            return await self._move_file(task.parameters)
        elif action == "delete":
            return await self._delete_file(task.parameters)
        elif action == "read":
            return await self._read_file(task.parameters)
        elif action == "write":
            return await self._write_file(task.parameters)
        else:
            raise ValueError(f"Unknown file operation: {action}")
    
    async def _handle_gui_automation(self, task: AutomationTask) -> Dict[str, Any]:
        """Handle GUI automation tasks"""
        if not GUI_AVAILABLE:
            raise Exception("GUI automation not available")
        
        action = task.parameters.get("action")
        
        if action == "click":
            return await self._click_element(task.parameters)
        elif action == "type":
            return await self._type_text(task.parameters)
        elif action == "screenshot":
            return await self._take_screenshot(task.parameters)
        elif action == "find_element":
            return await self._find_element(task.parameters)
        elif action == "drag":
            return await self._drag_element(task.parameters)
        else:
            raise ValueError(f"Unknown GUI action: {action}")
    
    async def _handle_system_tasks(self, task: AutomationTask) -> Dict[str, Any]:
        """Handle system-level tasks"""
        action = task.parameters.get("action")
        
        if action == "run_command":
            return await self._run_command(task.parameters)
        elif action == "get_system_info":
            return await self._get_system_info()
        elif action == "manage_services":
            return await self._manage_services(task.parameters)
        else:
            raise ValueError(f"Unknown system action: {action}")
    
    async def _open_application(self, app_name: str, params: Dict) -> Dict[str, Any]:
        """Open an application"""
        try:
            system = platform.system()
            
            if system == "Windows":
                # Try common Windows applications
                app_commands = {
                    "notepad": "notepad.exe",
                    "calculator": "calc.exe",
                    "paint": "mspaint.exe",
                    "excel": "excel.exe",
                    "word": "winword.exe",
                    "powerpoint": "powerpnt.exe",
                    "chrome": "chrome.exe",
                    "firefox": "firefox.exe",
                    "edge": "msedge.exe"
                }
                
                command = app_commands.get(app_name.lower(), app_name)
                
            elif system == "Darwin":  # macOS
                app_commands = {
                    "textedit": "TextEdit",
                    "calculator": "Calculator",
                    "safari": "Safari",
                    "chrome": "Google Chrome",
                    "firefox": "Firefox",
                    "excel": "Microsoft Excel",
                    "word": "Microsoft Word",
                    "powerpoint": "Microsoft PowerPoint"
                }
                
                app_bundle = app_commands.get(app_name.lower(), app_name)
                command = ["open", "-a", app_bundle]
                
            else:  # Linux
                app_commands = {
                    "gedit": "gedit",
                    "calculator": "gnome-calculator",
                    "firefox": "firefox",
                    "chrome": "google-chrome",
                    "libreoffice": "libreoffice"
                }
                
                command = app_commands.get(app_name.lower(), app_name)
            
            # Execute command
            if isinstance(command, list):
                process = await asyncio.create_subprocess_exec(*command)
            else:
                process = await asyncio.create_subprocess_shell(command)
            
            # Wait a moment for the app to start
            await asyncio.sleep(2)
            
            return {
                "success": True,
                "app_name": app_name,
                "pid": process.pid if process else None,
                "message": f"Successfully opened {app_name}"
            }
            
        except Exception as e:
            raise Exception(f"Failed to open {app_name}: {str(e)}")
    
    async def _close_application(self, app_name: str) -> Dict[str, Any]:
        """Close an application"""
        try:
            if not GUI_AVAILABLE:
                raise Exception("GUI automation not available")
            
            # Find windows with the app name
            windows = gw.getWindowsWithTitle(app_name)
            closed_count = 0
            
            for window in windows:
                try:
                    window.close()
                    closed_count += 1
                except:
                    pass
            
            return {
                "success": True,
                "app_name": app_name,
                "closed_windows": closed_count,
                "message": f"Closed {closed_count} windows for {app_name}"
            }
            
        except Exception as e:
            raise Exception(f"Failed to close {app_name}: {str(e)}")
    
    async def _focus_application(self, app_name: str) -> Dict[str, Any]:
        """Focus an application window"""
        try:
            if not GUI_AVAILABLE:
                raise Exception("GUI automation not available")
            
            windows = gw.getWindowsWithTitle(app_name)
            if not windows:
                raise Exception(f"No windows found for {app_name}")
            
            window = windows[0]
            window.activate()
            
            return {
                "success": True,
                "app_name": app_name,
                "window_title": window.title,
                "message": f"Focused window: {window.title}"
            }
            
        except Exception as e:
            raise Exception(f"Failed to focus {app_name}: {str(e)}")
    
    async def _list_applications(self) -> Dict[str, Any]:
        """List running applications"""
        try:
            if not GUI_AVAILABLE:
                raise Exception("GUI automation not available")
            
            windows = gw.getAllWindows()
            app_list = []
            
            for window in windows:
                if window.title and window.visible:
                    app_list.append({
                        "title": window.title,
                        "left": window.left,
                        "top": window.top,
                        "width": window.width,
                        "height": window.height,
                        "visible": window.visible,
                        "minimized": window.isMinimized,
                        "maximized": window.isMaximized
                    })
            
            return {
                "success": True,
                "applications": app_list,
                "count": len(app_list)
            }
            
        except Exception as e:
            raise Exception(f"Failed to list applications: {str(e)}")
    
    async def _create_file(self, params: Dict) -> Dict[str, Any]:
        """Create a file"""
        try:
            file_path = Path(params["path"])
            content = params.get("content", "")
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": str(file_path),
                "size": len(content),
                "message": f"Created file: {file_path}"
            }
            
        except Exception as e:
            raise Exception(f"Failed to create file: {str(e)}")
    
    async def _copy_file(self, params: Dict) -> Dict[str, Any]:
        """Copy a file"""
        try:
            import shutil
            
            source = Path(params["source"])
            destination = Path(params["destination"])
            
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source, destination)
            
            return {
                "success": True,
                "source": str(source),
                "destination": str(destination),
                "message": f"Copied {source} to {destination}"
            }
            
        except Exception as e:
            raise Exception(f"Failed to copy file: {str(e)}")
    
    async def _click_element(self, params: Dict) -> Dict[str, Any]:
        """Click on screen coordinates or find and click element"""
        try:
            if not GUI_AVAILABLE:
                raise Exception("GUI automation not available")
            
            x = params.get("x")
            y = params.get("y")
            
            if x is not None and y is not None:
                # Click at specific coordinates
                pyautogui.click(x, y)
                return {
                    "success": True,
                    "x": x,
                    "y": y,
                    "message": f"Clicked at ({x}, {y})"
                }
            else:
                # Find element by image or text (future implementation)
                raise Exception("Element finding not yet implemented")
                
        except Exception as e:
            raise Exception(f"Failed to click: {str(e)}")
    
    async def _type_text(self, params: Dict) -> Dict[str, Any]:
        """Type text"""
        try:
            if not GUI_AVAILABLE:
                raise Exception("GUI automation not available")
            
            text = params["text"]
            interval = params.get("interval", 0.01)
            
            pyautogui.typewrite(text, interval=interval)
            
            return {
                "success": True,
                "text": text,
                "length": len(text),
                "message": f"Typed {len(text)} characters"
            }
            
        except Exception as e:
            raise Exception(f"Failed to type text: {str(e)}")
    
    async def _take_screenshot(self, params: Dict) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            if not GUI_AVAILABLE:
                raise Exception("GUI automation not available")
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            
            # Save to temp directory
            temp_dir = self.config.get_temp_path()
            screenshot_path = temp_dir / f"screenshot_{int(time.time())}.png"
            screenshot.save(screenshot_path)
            
            return {
                "success": True,
                "path": str(screenshot_path),
                "size": screenshot.size,
                "message": f"Screenshot saved to {screenshot_path}"
            }
            
        except Exception as e:
            raise Exception(f"Failed to take screenshot: {str(e)}")
    
    async def _run_command(self, params: Dict) -> Dict[str, Any]:
        """Run system command"""
        try:
            command = params["command"]
            shell = params.get("shell", True)
            timeout = params.get("timeout", 30)
            
            if shell:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *command.split(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f"Command timed out after {timeout} seconds")
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "command": command
            }
            
        except Exception as e:
            raise Exception(f"Failed to run command: {str(e)}")
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            import psutil
            
            return {
                "success": True,
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": {
                    "total": psutil.disk_usage('/').total,
                    "used": psutil.disk_usage('/').used,
                    "free": psutil.disk_usage('/').free
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to get system info: {str(e)}")
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed task results"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            tasks_to_remove = []
            for task_id, result in self.task_results.items():
                if hasattr(result, 'timestamp'):
                    if current_time - result.timestamp > max_age_seconds:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.task_results[task_id]
            
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} old task results")
            return len(tasks_to_remove)
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup tasks: {e}")
            return 0
    
    def get_automation_stats(self) -> Dict[str, Any]:
        """Get automation service statistics"""
        return {
            "gui_available": GUI_AVAILABLE,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.task_results),
            "platform": platform.system(),
            "screen_size": self.get_screen_info() if GUI_AVAILABLE else None
        }ncel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            self.logger.info(f"Cancelled task: {task_id}")
            return True
        return False
    
    async def get_task_status(self, task_id: str) -> Optional[AutomationResult]:
        """Get task result"""
        return self.task_results.get(task_id)  
  
    async def analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
        """Analyze screenshot for UI elements and text"""
        try:
            from PIL import Image
            import pytesseract
            
            # Load screenshot
            image = Image.open(screenshot_path)
            
            # Extract text using OCR
            extracted_text = pytesseract.image_to_string(image)
            
            # Get image dimensions
            width, height = image.size
            
            # Basic UI element detection (simplified)
            ui_elements = await self._detect_ui_elements(image)
            
            return {
                'success': True,
                'action': 'analyze_screenshot',
                'text': extracted_text.strip(),
                'dimensions': [width, height],
                'ui_elements': ui_elements,
                'file_path': screenshot_path
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _detect_ui_elements(self, image) -> List[Dict[str, Any]]:
        """Detect UI elements in screenshot (simplified implementation)"""
        try:
            import cv2
            import numpy as np
            
            # Convert PIL image to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            
            # Detect buttons using template matching (simplified)
            elements = []
            
            # Detect rectangular regions that might be buttons
            contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size to find button-like elements
                if 50 < w < 300 and 20 < h < 100:
                    elements.append({
                        'type': 'button',
                        'bounds': [x, y, w, h],
                        'center': [x + w//2, y + h//2],
                        'confidence': 0.7
                    })
            
            return elements[:10]  # Return top 10 elements
            
        except Exception as e:
            self.logger.warning(f"UI element detection failed: {e}")
            return []
    
    async def find_element_by_text(self, text: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """Find UI element by text content"""
        try:
            if not screenshot_path:
                # Take a new screenshot
                screenshot_result = await self._handle_screenshot({})
                if not screenshot_result['success']:
                    return screenshot_result
                screenshot_path = screenshot_result.get('file_path')
            
            # Analyze screenshot
            analysis = await self.analyze_screenshot(screenshot_path)
            if not analysis['success']:
                return analysis
            
            # Search for text in extracted content
            extracted_text = analysis['text'].lower()
            search_text = text.lower()
            
            if search_text in extracted_text:
                # For now, return approximate location
                # In a full implementation, this would use OCR bounding boxes
                return {
                    'success': True,
                    'found': True,
                    'text': text,
                    'approximate_location': [400, 300]  # Center of typical screen
                }
            else:
                return {
                    'success': True,
                    'found': False,
                    'text': text
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_automation_script(self, steps: List[Dict[str, Any]]) -> str:
        """Create a reusable automation script from a sequence of steps"""
        try:
            script_id = str(uuid.uuid4())
            script_path = self.config.get_data_path("automation_scripts") / f"{script_id}.json"
            script_path.parent.mkdir(exist_ok=True)
            
            script_data = {
                'id': script_id,
                'created_at': time.time(),
                'steps': steps,
                'metadata': {
                    'total_steps': len(steps),
                    'estimated_duration': len(steps) * 2  # 2 seconds per step estimate
                }
            }
            
            with open(script_path, 'w') as f:
                json.dump(script_data, f, indent=2)
            
            return {
                'success': True,
                'script_id': script_id,
                'script_path': str(script_path),
                'steps_count': len(steps)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def execute_automation_script(self, script_id: str) -> Dict[str, Any]:
        """Execute a saved automation script"""
        try:
            script_path = self.config.get_data_path("automation_scripts") / f"{script_id}.json"
            
            if not script_path.exists():
                return {'success': False, 'error': f'Script {script_id} not found'}
            
            with open(script_path, 'r') as f:
                script_data = json.load(f)
            
            results = []
            for i, step in enumerate(script_data['steps']):
                self.logger.info(f"Executing step {i+1}/{len(script_data['steps'])}: {step.get('type')}")
                
                result = await self.execute_automation(step)
                results.append(result)
                
                if not result['success']:
                    self.logger.error(f"Step {i+1} failed: {result.get('error')}")
                    break
                
                # Small delay between steps
                await asyncio.sleep(0.5)
            
            return {
                'success': True,
                'script_id': script_id,
                'steps_executed': len(results),
                'results': results
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_window_list(self) -> Dict[str, Any]:
        """Get list of all open windows with detailed information"""
        try:
            if not GUI_AVAILABLE:
                return {'success': False, 'error': 'GUI automation not available'}
            
            import psutil
            
            windows = []
            processes = []
            
            # Get window information
            try:
                import pygetwindow as gw
                for window in gw.getAllWindows():
                    if window.title.strip():
                        windows.append({
                            'title': window.title,
                            'left': window.left,
                            'top': window.top,
                            'width': window.width,
                            'height': window.height,
                            'visible': window.visible,
                            'minimized': window.isMinimized,
                            'maximized': window.isMaximized,
                            'active': window.isActive
                        })
            except Exception as e:
                self.logger.warning(f"Window enumeration failed: {e}")
            
            # Get process information
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'cpu_percent': proc.info['cpu_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'success': True,
                'windows': windows,
                'processes': processes[:20],  # Top 20 processes
                'total_windows': len(windows),
                'total_processes': len(processes)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_safe_execution_environment(self) -> Dict[str, Any]:
        """Create a safe execution environment with user permission system"""
        try:
            # Create sandbox directory
            sandbox_dir = self.config.get_data_path("automation_sandbox")
            sandbox_dir.mkdir(exist_ok=True)
            
            # Create permissions file
            permissions_file = sandbox_dir / "permissions.json"
            
            default_permissions = {
                'allow_file_operations': False,
                'allow_network_access': False,
                'allow_system_commands': False,
                'allowed_applications': [],
                'blocked_applications': ['cmd.exe', 'powershell.exe', 'bash', 'terminal'],
                'max_execution_time': 300,  # 5 minutes
                'require_confirmation': True
            }
            
            if not permissions_file.exists():
                with open(permissions_file, 'w') as f:
                    json.dump(default_permissions, f, indent=2)
            
            return {
                'success': True,
                'sandbox_dir': str(sandbox_dir),
                'permissions_file': str(permissions_file),
                'default_permissions': default_permissions
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def check_automation_permissions(self, task: Dict[str, Any]) -> bool:
        """Check if automation task is permitted by security policy"""
        try:
            sandbox_dir = self.config.get_data_path("automation_sandbox")
            permissions_file = sandbox_dir / "permissions.json"
            
            if not permissions_file.exists():
                await self.create_safe_execution_environment()
            
            with open(permissions_file, 'r') as f:
                permissions = json.load(f)
            
            task_type = task.get('type', '')
            
            # Check specific permissions
            if task_type in ['open_application', 'close_application']:
                app_name = task.get('application', '').lower()
                if app_name in permissions.get('blocked_applications', []):
                    return False
                
                allowed_apps = permissions.get('allowed_applications', [])
                if allowed_apps and app_name not in allowed_apps:
                    return False
            
            # Check for dangerous operations
            dangerous_operations = ['system_command', 'file_delete', 'registry_edit']
            if task_type in dangerous_operations and not permissions.get('allow_system_commands', False):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Permission check failed: {e}")
            return False
    
    def get_automation_stats(self) -> Dict[str, Any]:
        """Get automation service statistics"""
        return {
            'gui_available': GUI_AVAILABLE,
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.task_results),
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'screen_size': list(pyautogui.size()) if GUI_AVAILABLE else None,
            'mouse_position': list(pyautogui.position()) if GUI_AVAILABLE else None
        }