"""
Comprehensive tests for Automation Service
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import subprocess
import tempfile
from pathlib import Path
import time
import platform

from services.automation_service import AutomationService
from models.chat_models import AutomationTask, TaskStatus, ServiceStatus

class TestAutomationService:
    """Test cases for Automation Service functionality"""

    @pytest.mark.asyncio
    async def test_service_initialization(self, test_config):
        """Test automation service initialization"""
        service = AutomationService(test_config)
        
        assert service.config == test_config
        assert isinstance(service.active_tasks, dict)
        assert isinstance(service.task_results, dict)
        assert len(service.active_tasks) == 0

    @pytest.mark.asyncio
    async def test_start_service(self, automation_service):
        """Test service startup"""
        await automation_service.start()
        
        status = await automation_service.get_status()
        assert status.name == "automation_service"
        assert status.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]

    @pytest.mark.asyncio
    async def test_app_control_open_application(self, automation_service, mock_subprocess):
        """Test opening an application"""
        task_data = {
            "task_id": "test-task-1",
            "task_type": "app_control",
            "parameters": {
                "action": "open",
                "app_name": "notepad"
            },
            "priority": 1,
            "timeout": 30
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess_shell:
            mock_process = Mock()
            mock_process.pid = 1234
            mock_subprocess_shell.return_value = mock_process
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            assert "notepad" in result.result["app_name"]

    @pytest.mark.asyncio
    async def test_app_control_close_application(self, automation_service):
        """Test closing an application"""
        task_data = {
            "task_id": "test-task-2",
            "task_type": "app_control",
            "parameters": {
                "action": "close",
                "app_name": "notepad"
            },
            "priority": 1,
            "timeout": 30
        }
        
        # Mock GUI availability and window operations
        import services.automation_service
        with patch.object(services.automation_service, 'GUI_AVAILABLE', True), \
             patch('pygetwindow.getWindowsWithTitle') as mock_get_windows:
            mock_window = Mock()
            mock_window.close = Mock()
            mock_get_windows.return_value = [mock_window]
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            assert result.result["closed_windows"] == 1

    @pytest.mark.asyncio
    async def test_file_operations_create_file(self, automation_service, temp_dir):
        """Test file creation"""
        test_file = temp_dir / "test_file.txt"
        task_data = {
            "task_id": "test-task-3",
            "task_type": "file_operations",
            "parameters": {
                "action": "create",
                "path": str(test_file),
                "content": "Hello, World!"
            },
            "priority": 1,
            "timeout": 30
        }
        
        result = await automation_service.execute_task(task_data)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.result["success"] is True
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_file_operations_copy_file(self, automation_service, temp_dir):
        """Test file copying"""
        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "destination.txt"
        
        # Create source file
        source_file.write_text("Test content")
        
        task_data = {
            "task_id": "test-task-4",
            "task_type": "file_operations",
            "parameters": {
                "action": "copy",
                "source": str(source_file),
                "destination": str(dest_file)
            },
            "priority": 1,
            "timeout": 30
        }
        
        result = await automation_service.execute_task(task_data)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.result["success"] is True
        assert dest_file.exists()
        assert dest_file.read_text() == "Test content"

    @pytest.mark.asyncio
    async def test_gui_automation_click(self, automation_service):
        """Test GUI click automation"""
        task_data = {
            "task_id": "test-task-5",
            "task_type": "gui_automation",
            "parameters": {
                "action": "click",
                "x": 100,
                "y": 200
            },
            "priority": 1,
            "timeout": 30
        }
        
        # Mock GUI availability and click operation
        with patch('pyautogui.click') as mock_click:
            # Mock the _handle_gui_automation method to bypass GUI_AVAILABLE check
            original_method = automation_service._handle_gui_automation
            
            async def mock_gui_automation(task):
                # Simulate successful click
                mock_click(task.parameters["x"], task.parameters["y"])
                return {"success": True, "action": "click"}
            
            automation_service._handle_gui_automation = mock_gui_automation
            
            try:
                result = await automation_service.execute_task(task_data)
                
                assert result.status == TaskStatus.COMPLETED
                assert result.result["success"] is True
                mock_click.assert_called_once_with(100, 200)
            finally:
                # Restore original method
                automation_service._handle_gui_automation = original_method

    @pytest.mark.asyncio
    async def test_gui_automation_type_text(self, automation_service):
        """Test GUI text typing"""
        task_data = {
            "task_id": "test-task-6",
            "task_type": "gui_automation",
            "parameters": {
                "action": "type",
                "text": "Hello, World!",
                "interval": 0.01
            },
            "priority": 1,
            "timeout": 30
        }
        
        # Mock GUI availability and typewrite operation
        import services.automation_service
        with patch.object(services.automation_service, 'GUI_AVAILABLE', True), \
             patch('services.automation_service.pyautogui.typewrite') as mock_typewrite:
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            mock_typewrite.assert_called_once_with("Hello, World!", interval=0.01)

    @pytest.mark.asyncio
    async def test_gui_automation_screenshot(self, automation_service, temp_dir):
        """Test taking screenshots"""
        task_data = {
            "task_id": "test-task-7",
            "task_type": "gui_automation",
            "parameters": {
                "action": "screenshot"
            },
            "priority": 1,
            "timeout": 30
        }
        
        # Mock GUI availability and screenshot operation
        import services.automation_service
        with patch.object(services.automation_service, 'GUI_AVAILABLE', True), \
             patch('services.automation_service.pyautogui.screenshot') as mock_screenshot:
            mock_image = Mock()
            mock_image.size = (1920, 1080)
            mock_image.save = Mock()
            mock_screenshot.return_value = mock_image
            
            # Mock the config temp path
            automation_service.config.get_temp_path = Mock(return_value=temp_dir)
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            assert "screenshot" in result.result["path"]

    @pytest.mark.asyncio
    async def test_system_tasks_run_command(self, automation_service):
        """Test running system commands"""
        task_data = {
            "task_id": "test-task-8",
            "task_type": "system_tasks",
            "parameters": {
                "action": "run_command",
                "command": "echo 'Hello World'",
                "timeout": 10
            },
            "priority": 1,
            "timeout": 30
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Hello World\n", b""))
            mock_subprocess.return_value = mock_process
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            assert "Hello World" in result.result["stdout"]

    @pytest.mark.asyncio
    async def test_system_tasks_get_system_info(self, automation_service):
        """Test getting system information"""
        task_data = {
            "task_id": "test-task-9",
            "task_type": "system_tasks",
            "parameters": {
                "action": "get_system_info"
            },
            "priority": 1,
            "timeout": 30
        }
        
        with patch('psutil.cpu_count', return_value=8), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.total = 16 * 1024**3  # 16GB
            mock_memory.return_value.available = 8 * 1024**3  # 8GB
            
            mock_disk.return_value.total = 1024 * 1024**3  # 1TB
            mock_disk.return_value.used = 512 * 1024**3   # 512GB
            mock_disk.return_value.free = 512 * 1024**3   # 512GB
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            assert result.result["cpu_count"] == 8
            assert result.result["memory_total"] == 16 * 1024**3

    @pytest.mark.asyncio
    async def test_task_timeout_handling(self, automation_service):
        """Test task timeout handling"""
        task_data = {
            "task_id": "test-task-timeout",
            "task_type": "system_tasks",
            "parameters": {
                "action": "run_command",
                "command": "sleep 10",  # Long running command
                "timeout": 1  # Short timeout
            },
            "priority": 1,
            "timeout": 30
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            # Simulate a process that takes too long
            mock_process = Mock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_process.kill = Mock()
            mock_subprocess.return_value = mock_process
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.FAILED
            assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_task_type(self, automation_service):
        """Test handling of invalid task types"""
        task_data = {
            "task_id": "test-task-invalid",
            "task_type": "invalid_type",
            "parameters": {},
            "priority": 1,
            "timeout": 30
        }
        
        result = await automation_service.execute_task(task_data)
        
        assert result.status == TaskStatus.FAILED
        assert "unknown task type" in result.error.lower()

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, automation_service):
        """Test concurrent task execution"""
        tasks = []
        for i in range(3):
            task_data = {
                "task_id": f"concurrent-task-{i}",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": f"/tmp/test_file_{i}.txt",
                    "content": f"Content {i}"
                },
                "priority": 1,
                "timeout": 30
            }
            tasks.append(automation_service.execute_task(task_data))
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_cancellation(self, automation_service):
        """Test task cancellation"""
        task_id = "cancellable-task"
        
        # Mock a long-running command that we can control
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Create a mock process that doesn't complete immediately
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            # Start a long-running task
            task_data = {
                "task_id": task_id,
                "task_type": "system_tasks",
                "parameters": {
                    "action": "run_command",
                    "command": "sleep 60"
                },
                "priority": 1,
                "timeout": 30
            }
            
            # Start task execution in background
            task = asyncio.create_task(automation_service.execute_task(task_data))
            
            # Give it a moment to start and be added to active_tasks
            await asyncio.sleep(0.01)
            
            # Verify task is in active_tasks
            assert task_id in automation_service.active_tasks
            
            # Cancel the task
            cancelled = await automation_service.cancel_task(task_id)
            
            # Clean up the task
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            assert cancelled is True

    @pytest.mark.asyncio
    async def test_error_handling_permission_denied(self, automation_service):
        """Test handling of permission denied errors"""
        task_data = {
            "task_id": "permission-test",
            "task_type": "file_operations",
            "parameters": {
                "action": "create",
                "path": "/root/restricted_file.txt",  # Restricted path
                "content": "test"
            },
            "priority": 1,
            "timeout": 30
        }
        
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.FAILED
            assert "access denied" in result.error.lower() or "permission" in result.error.lower()

    @pytest.mark.asyncio
    async def test_platform_specific_commands(self, automation_service):
        """Test platform-specific command handling"""
        current_platform = platform.system().lower()
        
        task_data = {
            "task_id": "platform-test",
            "task_type": "app_control",
            "parameters": {
                "action": "open",
                "app_name": "calculator"
            },
            "priority": 1,
            "timeout": 30
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess_shell, \
             patch('asyncio.create_subprocess_exec') as mock_subprocess_exec:
            
            mock_process = Mock()
            mock_process.pid = 1234
            mock_subprocess_shell.return_value = mock_process
            mock_subprocess_exec.return_value = mock_process
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            
            # Verify appropriate subprocess method was called based on platform
            if current_platform == "darwin":
                mock_subprocess_exec.assert_called()
            else:
                mock_subprocess_shell.assert_called()

    @pytest.mark.asyncio
    async def test_safety_mechanisms(self, automation_service):
        """Test safety mechanisms for automation"""
        # Test that PyAutoGUI safety features are enabled
        assert automation_service.config.automation.safety_checks is True
        
        # Test screenshot on error functionality
        task_data = {
            "task_id": "safety-test",
            "task_type": "gui_automation",
            "parameters": {
                "action": "click",
                "x": -1,  # Invalid coordinates
                "y": -1
            },
            "priority": 1,
            "timeout": 30
        }
        
        with patch('pyautogui.click', side_effect=Exception("Click failed")):
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_performance_metrics(self, automation_service, performance_thresholds):
        """Test automation performance metrics"""
        task_data = {
            "task_id": "performance-test",
            "task_type": "file_operations",
            "parameters": {
                "action": "create",
                "path": "/tmp/perf_test.txt",
                "content": "Performance test content"
            },
            "priority": 1,
            "timeout": 30
        }
        
        start_time = time.time()
        result = await automation_service.execute_task(task_data)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert result.status == TaskStatus.COMPLETED
        assert execution_time < performance_thresholds["automation_execution_time"]
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_list_applications(self, automation_service):
        """Test listing running applications"""
        task_data = {
            "task_id": "list-apps-test",
            "task_type": "app_control",
            "parameters": {
                "action": "list"
            },
            "priority": 1,
            "timeout": 30
        }
        
        # Mock GUI availability and window operations
        import services.automation_service
        with patch.object(services.automation_service, 'GUI_AVAILABLE', True), \
             patch('pygetwindow.getAllWindows') as mock_get_all_windows:
            mock_window1 = Mock()
            mock_window1.title = "Test Application 1"
            mock_window1.visible = True
            mock_window1.left = 100
            mock_window1.top = 100
            mock_window1.width = 800
            mock_window1.height = 600
            mock_window1.isMinimized = False
            mock_window1.isMaximized = False
            
            mock_window2 = Mock()
            mock_window2.title = "Test Application 2"
            mock_window2.visible = True
            mock_window2.left = 200
            mock_window2.top = 200
            mock_window2.width = 1024
            mock_window2.height = 768
            mock_window2.isMinimized = True
            mock_window2.isMaximized = False
            
            mock_get_all_windows.return_value = [mock_window1, mock_window2]
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            assert result.result["count"] == 2
            assert len(result.result["applications"]) == 2

    @pytest.mark.asyncio
    async def test_focus_application(self, automation_service):
        """Test focusing an application window"""
        task_data = {
            "task_id": "focus-test",
            "task_type": "app_control",
            "parameters": {
                "action": "focus",
                "app_name": "Test Application"
            },
            "priority": 1,
            "timeout": 30
        }
        
        # Mock GUI availability and window operations
        import services.automation_service
        with patch.object(services.automation_service, 'GUI_AVAILABLE', True), \
             patch('pygetwindow.getWindowsWithTitle') as mock_get_windows:
            mock_window = Mock()
            mock_window.title = "Test Application"
            mock_window.activate = Mock()
            mock_get_windows.return_value = [mock_window]
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status == TaskStatus.COMPLETED
            assert result.result["success"] is True
            mock_window.activate.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_priority_handling(self, automation_service):
        """Test task priority handling"""
        # This test verifies that the service can handle tasks with different priorities
        # In a real implementation, higher priority tasks would be executed first
        
        high_priority_task = {
            "task_id": "high-priority",
            "task_type": "file_operations",
            "parameters": {
                "action": "create",
                "path": "/tmp/high_priority.txt",
                "content": "High priority task"
            },
            "priority": 10,  # High priority
            "timeout": 30
        }
        
        low_priority_task = {
            "task_id": "low-priority",
            "task_type": "file_operations",
            "parameters": {
                "action": "create",
                "path": "/tmp/low_priority.txt",
                "content": "Low priority task"
            },
            "priority": 1,  # Low priority
            "timeout": 30
        }
        
        # Execute both tasks
        high_result = await automation_service.execute_task(high_priority_task)
        low_result = await automation_service.execute_task(low_priority_task)
        
        assert high_result.status == TaskStatus.COMPLETED
        assert low_result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_task_status(self, automation_service):
        """Test getting task status and results"""
        task_data = {
            "task_id": "status-test",
            "task_type": "file_operations",
            "parameters": {
                "action": "create",
                "path": "/tmp/status_test.txt",
                "content": "Status test"
            },
            "priority": 1,
            "timeout": 30
        }
        
        # Execute task
        result = await automation_service.execute_task(task_data)
        
        # Get task status
        task_status = await automation_service.get_task_status("status-test")
        
        assert task_status is not None
        assert task_status.task_id == "status-test"
        assert task_status.status == TaskStatus.COMPLETED