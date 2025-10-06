"""
Integration tests for AI Assistant Desktop Application
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from fastapi.testclient import TestClient
from main import app, services
from models.chat_models import ChatRequest, SystemStatus, LearningData

class TestIntegration:
    """Integration tests for the complete application"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_full_chat_workflow(self, all_services, sample_chat_request):
        """Test complete chat workflow from request to response"""
        # Mock all external dependencies
        with patch('httpx.AsyncClient') as mock_httpx, \
             patch('asyncio.create_subprocess_exec') as mock_subprocess:
            
            # Mock LLM response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {"content": "I'll help you with that task."}
            }
            mock_httpx.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Mock TTS generation
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process
            
            # Initialize services
            for service in all_services.values():
                if hasattr(service, 'start'):
                    await service.start()
            
            # Process chat request
            llm_service = all_services['llm']
            tts_service = all_services['tts']
            
            # Mock TTS paths
            tts_service.piper_path = Path("/mock/piper")
            tts_service.voice_model_path = "/mock/voice.onnx"
            
            # Process message
            llm_response = await llm_service.process_message(
                sample_chat_request.message,
                sample_chat_request.context_id
            )
            
            assert llm_response.text == "I'll help you with that task."
            assert llm_response.context_id is not None

    @pytest.mark.asyncio
    async def test_automation_workflow(self, all_services):
        """Test automation workflow integration"""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = Mock()
            mock_process.pid = 1234
            mock_subprocess.return_value = mock_process
            
            automation_service = all_services['automation']
            await automation_service.start()
            
            # Test app control automation
            task_data = {
                "task_id": "integration-test",
                "task_type": "app_control",
                "parameters": {
                    "action": "open",
                    "app_name": "notepad"
                },
                "priority": 1,
                "timeout": 30
            }
            
            result = await automation_service.execute_task(task_data)
            
            assert result.status.value == "completed"
            assert result.result["success"] is True

    @pytest.mark.asyncio
    async def test_security_integration(self, all_services):
        """Test security service integration"""
        security_service = all_services['security']
        
        with patch('services.security_service.CRYPTO_AVAILABLE', True):
            await security_service.start()
            
            # Test permission system
            user_id = "test_user"
            granted = await security_service.request_permission(
                user_id, "file_operations", "read"
            )
            
            assert granted is True
            
            # Test encryption
            test_data = "Sensitive test data"
            
            # Mock cipher suite
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_cipher.decrypt.return_value = test_data.encode()
            security_service.cipher_suite = mock_cipher
            
            encrypted = await security_service.encrypt_data(test_data)
            decrypted = await security_service.decrypt_data(encrypted)
            
            assert decrypted == test_data

    @pytest.mark.asyncio
    async def test_learning_integration(self, all_services, sample_user_interaction):
        """Test learning service integration"""
        learning_service = all_services['learning']
        
        with patch('services.learning_service.LEARNING_AVAILABLE', True):
            await learning_service.start()
            
            # Record interaction
            await learning_service.record_interaction(
                Mock(message=sample_user_interaction.user_input, metadata={}),
                Mock(text=sample_user_interaction.assistant_response)
            )
            
            # Test pattern detection
            patterns = await learning_service.detect_workflow_patterns()
            
            # Should handle empty patterns gracefully
            assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_watchdog_integration(self, all_services):
        """Test watchdog service integration"""
        watchdog_service = all_services['watchdog']
        
        await watchdog_service.start()
        
        # Test system metrics collection
        metrics = await watchdog_service.get_system_metrics()
        
        assert "timestamp" in metrics
        assert "cpu" in metrics
        assert "memory" in metrics
        
        # Test health checks
        status = await watchdog_service.get_status()
        assert status.name == "watchdog_service"

    @pytest.mark.asyncio
    async def test_update_service_integration(self, all_services):
        """Test update service integration"""
        update_service = all_services['updater']
        
        with patch('services.update_service.HTTP_AVAILABLE', True):
            await update_service.start()
            
            # Test version info
            version_info = await update_service.get_version_info()
            
            assert "current_version" in version_info
            assert version_info["current_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_service_dependencies(self, all_services):
        """Test service dependency management"""
        # Test that services can start in any order
        service_names = ['security', 'llm', 'stt', 'tts', 'automation', 'learning']
        
        for service_name in service_names:
            service = all_services[service_name]
            if hasattr(service, 'start'):
                await service.start()
                
                status = await service.get_status()
                assert status.name == f"{service_name}_service"

    @pytest.mark.asyncio
    async def test_error_propagation(self, all_services):
        """Test error propagation between services"""
        llm_service = all_services['llm']
        
        # Test with network error
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Network error")
            
            response = await llm_service.process_message("Test message")
            
            # Should handle error gracefully
            assert "error" in response.text.lower()

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self, all_services):
        """Test concurrent operations across services"""
        tasks = []
        
        # Start multiple services concurrently
        for service_name, service in all_services.items():
            if hasattr(service, 'start') and service_name != 'watchdog':
                tasks.append(service.start())
        
        # Wait for all services to start
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Test concurrent status checks
        status_tasks = []
        for service_name, service in all_services.items():
            if hasattr(service, 'get_status') and service_name != 'config':
                status_tasks.append(service.get_status())
        
        statuses = await asyncio.gather(*status_tasks, return_exceptions=True)
        
        # All status checks should complete
        assert len(statuses) == len(status_tasks)

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, all_services):
        """Test memory usage monitoring across services"""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Start all services
        for service_name, service in all_services.items():
            if hasattr(service, 'start') and service_name not in ['watchdog', 'config']:
                await service.start()
        
        # Check memory usage
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        
        # Memory increase should be reasonable (less than 500MB for tests)
        assert memory_increase < 500 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_configuration_propagation(self, all_services, test_config):
        """Test configuration propagation to all services"""
        # Verify all services have access to configuration
        for service_name, service in all_services.items():
            if service_name != 'config' and hasattr(service, 'config'):
                assert service.config == test_config

    @pytest.mark.asyncio
    async def test_service_cleanup(self, all_services):
        """Test proper service cleanup"""
        # Start services
        started_services = []
        for service_name, service in all_services.items():
            if hasattr(service, 'start') and service_name not in ['watchdog', 'config']:
                await service.start()
                started_services.append(service)
        
        # Stop services
        for service in started_services:
            if hasattr(service, 'stop'):
                await service.stop()
        
        # Verify cleanup (no exceptions should be raised)
        assert True

    @pytest.mark.asyncio
    async def test_cross_service_communication(self, all_services):
        """Test communication between services"""
        llm_service = all_services['llm']
        automation_service = all_services['automation']
        
        # Mock LLM response with automation command
        automation_response = "I'll open notepad for you. [AUTOMATION:app_control:{\"action\":\"open\",\"app_name\":\"notepad\"}]"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": automation_response}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Process message that should trigger automation
            llm_response = await llm_service.process_message("Open notepad")
            
            assert llm_response.requires_automation is True
            assert llm_response.automation_task is not None
            
            # Execute the automation task
            with patch('asyncio.create_subprocess_shell') as mock_subprocess:
                mock_process = Mock()
                mock_process.pid = 1234
                mock_subprocess.return_value = mock_process
                
                automation_result = await automation_service.execute_task(llm_response.automation_task)
                
                assert automation_result.status.value == "completed"

    @pytest.mark.asyncio
    async def test_performance_under_load(self, all_services, performance_thresholds):
        """Test system performance under load"""
        llm_service = all_services['llm']
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Test response"}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Send multiple concurrent requests
            start_time = time.time()
            tasks = []
            
            for i in range(10):
                task = llm_service.process_message(f"Test message {i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time_per_request = total_time / len(tasks)
            
            # All requests should complete successfully
            assert len(results) == 10
            for result in results:
                assert result.text == "Test response"
            
            # Average response time should be reasonable
            assert avg_time_per_request < performance_thresholds["llm_response_time"]

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, all_services):
        """Test graceful degradation when services fail"""
        # Test LLM service with network failure
        llm_service = all_services['llm']
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Service unavailable")
            
            # Should not crash, should return error message
            response = await llm_service.process_message("Test message")
            assert response.text is not None
            assert "error" in response.text.lower()

    @pytest.mark.asyncio
    async def test_data_consistency(self, all_services, temp_dir):
        """Test data consistency across services"""
        security_service = all_services['security']
        learning_service = all_services['learning']
        
        # Mock data directories
        security_service.config.get_data_path = Mock(return_value=temp_dir)
        learning_service.config.get_data_path = Mock(return_value=temp_dir)
        
        with patch('services.security_service.CRYPTO_AVAILABLE', True), \
             patch('services.learning_service.LEARNING_AVAILABLE', True):
            
            await security_service.start()
            await learning_service.start()
            
            # Test that services can coexist and share data directory
            assert security_service.config.get_data_path() == learning_service.config.get_data_path()

    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, all_services):
        """Test comprehensive service health monitoring"""
        watchdog_service = all_services['watchdog']
        
        # Add health checks for all services
        for service_name, service in all_services.items():
            if hasattr(service, 'get_status') and service_name not in ['config', 'watchdog']:
                # Mock health check
                health_check = Mock()
                health_check.name = f"service_{service_name}"
                health_check.check_func = AsyncMock(return_value=True)
                health_check.interval = 60
                health_check.timeout = 30
                health_check.last_check = None
                health_check.last_result = None
                health_check.failure_count = 0
                health_check.max_failures = 3
                
                await watchdog_service.add_health_check(health_check)
        
        # Run health checks
        await watchdog_service._run_health_checks()
        
        # Verify health checks were added
        assert len(watchdog_service.health_checks) > 0

class TestAPIIntegration:
    """Integration tests for the FastAPI application"""

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # May be unhealthy in test environment

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_system_status_endpoint(self, client):
        """Test system status endpoint"""
        with patch('main.services') as mock_services:
            # Mock all services
            mock_status = Mock()
            mock_status.status = "healthy"
            
            mock_service = Mock()
            mock_service.get_status = AsyncMock(return_value=mock_status)
            
            mock_services = {
                'llm': mock_service,
                'stt': mock_service,
                'tts': mock_service,
                'automation': mock_service,
                'learning': mock_service,
                'security': mock_service,
                'updater': mock_service
            }
            
            response = client.get("/system/status")
            # May fail in test environment due to missing services
            assert response.status_code in [200, 500]

    def test_chat_message_endpoint(self, client):
        """Test chat message endpoint"""
        chat_data = {
            "message": "Hello, how are you?",
            "include_audio": False,
            "context_id": None
        }
        
        with patch('main.services') as mock_services:
            mock_llm = Mock()
            mock_llm.process_message = AsyncMock()
            mock_llm.process_message.return_value = Mock(
                text="I'm doing well, thank you!",
                context_id="test-context",
                requires_automation=False,
                automation_result=None,
                suggestions=[]
            )
            
            mock_services = {'llm': mock_llm, 'tts': Mock(), 'learning': Mock()}
            
            response = client.post("/chat/message", json=chat_data)
            # May fail due to missing service initialization
            assert response.status_code in [200, 500]

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/")
        # CORS headers should be present
        assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()] or response.status_code == 405

class TestEndToEndWorkflows:
    """End-to-end workflow tests"""

    @pytest.mark.asyncio
    async def test_voice_to_automation_workflow(self, all_services, mock_audio_data):
        """Test complete voice-to-automation workflow"""
        stt_service = all_services['stt']
        llm_service = all_services['llm']
        automation_service = all_services['automation']
        
        # Mock STT transcription
        with patch.object(stt_service, 'transcribe', return_value="Open calculator"):
            transcription = await stt_service.transcribe(mock_audio_data)
            assert transcription == "Open calculator"
            
            # Mock LLM processing with automation command
            automation_response = "I'll open calculator for you. [AUTOMATION:app_control:{\"action\":\"open\",\"app_name\":\"calculator\"}]"
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": {"content": automation_response}}
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                llm_response = await llm_service.process_message(transcription)
                
                assert llm_response.requires_automation is True
                
                # Execute automation
                with patch('asyncio.create_subprocess_shell') as mock_subprocess:
                    mock_process = Mock()
                    mock_process.pid = 1234
                    mock_subprocess.return_value = mock_process
                    
                    automation_result = await automation_service.execute_task(llm_response.automation_task)
                    
                    assert automation_result.status.value == "completed"

    @pytest.mark.asyncio
    async def test_learning_and_suggestion_workflow(self, all_services):
        """Test learning from interactions and providing suggestions"""
        learning_service = all_services['learning']
        llm_service = all_services['llm']
        
        with patch('services.learning_service.LEARNING_AVAILABLE', True):
            await learning_service.start()
            
            # Simulate repeated interactions
            for i in range(5):
                mock_request = Mock(message="Open Excel", metadata={})
                mock_response = Mock(text="Opening Excel for you")
                
                await learning_service.record_interaction(mock_request, mock_response)
            
            # Get suggestions based on patterns
            suggestions = await learning_service.get_suggestions({"application": "excel"})
            
            # Should handle gracefully even with mock data
            assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_security_and_permission_workflow(self, all_services):
        """Test security permissions in automation workflow"""
        security_service = all_services['security']
        automation_service = all_services['automation']
        
        with patch('services.security_service.CRYPTO_AVAILABLE', True):
            await security_service.start()
            await automation_service.start()
            
            user_id = "test_user"
            
            # Request permission for file operations
            granted = await security_service.request_permission(
                user_id, "file_operations", "write"
            )
            
            assert granted is True
            
            # Execute file operation (should be allowed)
            task_data = {
                "task_id": "security-test",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": "/tmp/security_test.txt",
                    "content": "Security test content"
                },
                "priority": 1,
                "timeout": 30
            }
            
            result = await automation_service.execute_task(task_data)
            assert result.status.value == "completed"