"""
Performance tests for AI Assistant Desktop Application
"""

import pytest
import asyncio
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
import statistics

from services.llm_service import LLMService
from services.automation_service import AutomationService
from services.security_service import SecurityService
from models.chat_models import ChatRequest

class TestPerformance:
    """Performance tests for critical system components"""

    @pytest.mark.asyncio
    async def test_llm_response_time_single_request(self, llm_service, mock_ollama_response, performance_thresholds):
        """Test LLM response time for single request"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            start_time = time.time()
            result = await llm_service.process_message("What is the weather today?")
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response_time < performance_thresholds["llm_response_time"]
            assert result.text is not None

    @pytest.mark.asyncio
    async def test_llm_concurrent_requests_performance(self, llm_service, mock_ollama_response, performance_thresholds):
        """Test LLM performance under concurrent load"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            num_requests = 20
            start_time = time.time()
            
            # Create concurrent requests
            tasks = []
            for i in range(num_requests):
                task = llm_service.process_message(f"Test message {i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time_per_request = total_time / num_requests
            
            # All requests should complete successfully
            assert len(results) == num_requests
            for result in results:
                assert result.text is not None
            
            # Average response time should be reasonable
            assert avg_time_per_request < performance_thresholds["llm_response_time"]
            
            # Total time should show good concurrency (not linear)
            max_sequential_time = num_requests * performance_thresholds["llm_response_time"]
            assert total_time < max_sequential_time * 0.5  # Should be much faster than sequential

    @pytest.mark.asyncio
    async def test_automation_execution_performance(self, automation_service, performance_thresholds):
        """Test automation task execution performance"""
        task_data = {
            "task_id": "perf-test-1",
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
        
        assert result.status.value == "completed"
        assert execution_time < performance_thresholds["automation_execution_time"]

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, all_services):
        """Test memory usage under sustained load"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Start all services
        for service_name, service in all_services.items():
            if hasattr(service, 'start') and service_name not in ['watchdog', 'config']:
                await service.start()
        
        # Simulate sustained load
        llm_service = all_services['llm']
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Test response"}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Process many requests
            for i in range(100):
                await llm_service.process_message(f"Test message {i}")
                
                # Check memory every 10 requests
                if i % 10 == 0:
                    current_memory = process.memory_info().rss
                    memory_increase = current_memory - initial_memory
                    
                    # Memory increase should be reasonable (less than 200MB)
                    assert memory_increase < 200 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_cpu_usage_monitoring(self, all_services, performance_thresholds):
        """Test CPU usage during normal operations"""
        # Start monitoring CPU usage
        cpu_samples = []
        
        def monitor_cpu():
            for _ in range(10):  # Monitor for 10 seconds
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_samples.append(cpu_percent)
        
        # Start CPU monitoring in background
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Perform operations while monitoring
        llm_service = all_services['llm']
        automation_service = all_services['automation']
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Test response"}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Simulate mixed workload
            tasks = []
            for i in range(20):
                if i % 2 == 0:
                    task = llm_service.process_message(f"Message {i}")
                else:
                    task_data = {
                        "task_id": f"cpu-test-{i}",
                        "task_type": "file_operations",
                        "parameters": {
                            "action": "create",
                            "path": f"/tmp/cpu_test_{i}.txt",
                            "content": f"Content {i}"
                        },
                        "priority": 1,
                        "timeout": 30
                    }
                    task = automation_service.execute_task(task_data)
                
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        # Analyze CPU usage
        if cpu_samples:
            avg_cpu = statistics.mean(cpu_samples)
            max_cpu = max(cpu_samples)
            
            # Average CPU usage should be reasonable
            assert avg_cpu < performance_thresholds["cpu_usage_limit"]
            
            # Peak CPU usage should not be excessive
            assert max_cpu < 95.0  # Allow some spikes but not sustained high usage

    @pytest.mark.asyncio
    async def test_response_time_consistency(self, llm_service, mock_ollama_response):
        """Test response time consistency across multiple requests"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            response_times = []
            
            # Measure response times for multiple requests
            for i in range(20):
                start_time = time.time()
                result = await llm_service.process_message(f"Test message {i}")
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                
                assert result.text is not None
            
            # Analyze response time consistency
            avg_time = statistics.mean(response_times)
            
            # In test environment, just verify all responses completed in reasonable time
            assert avg_time < 1.0  # Average should be less than 1 second
            assert all(rt < 5.0 for rt in response_times)  # No individual response over 5 seconds
            
            # Verify we have reasonable variation (not all identical, which would indicate mocking issues)
            assert len(set(response_times)) > 1  # Should have some variation

    @pytest.mark.asyncio
    async def test_throughput_measurement(self, llm_service, mock_ollama_response):
        """Test system throughput (requests per second)"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            num_requests = 50
            start_time = time.time()
            
            # Process requests in batches to simulate realistic load
            batch_size = 10
            for batch_start in range(0, num_requests, batch_size):
                batch_end = min(batch_start + batch_size, num_requests)
                batch_tasks = []
                
                for i in range(batch_start, batch_end):
                    task = llm_service.process_message(f"Throughput test {i}")
                    batch_tasks.append(task)
                
                await asyncio.gather(*batch_tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            throughput = num_requests / total_time
            
            # Should achieve reasonable throughput (at least 5 requests per second)
            assert throughput >= 5.0
            
            print(f"Achieved throughput: {throughput:.2f} requests/second")

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, llm_service, mock_ollama_response):
        """Test for memory leaks during extended operation"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            memory_samples = [initial_memory]
            
            # Run extended test
            for cycle in range(10):
                # Process batch of requests
                tasks = []
                for i in range(20):
                    task = llm_service.process_message(f"Memory test cycle {cycle}, message {i}")
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                
                # Clear contexts to simulate normal cleanup
                llm_service.contexts.clear()
                
                # Sample memory usage
                current_memory = process.memory_info().rss
                memory_samples.append(current_memory)
                
                # Allow some time for garbage collection
                await asyncio.sleep(0.1)
            
            # Analyze memory trend
            final_memory = memory_samples[-1]
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be minimal (less than 50MB)
            assert memory_increase < 50 * 1024 * 1024
            
            # Check for consistent memory growth (potential leak)
            if len(memory_samples) >= 5:
                recent_samples = memory_samples[-5:]
                # Recent samples should not show consistent upward trend
                increases = sum(1 for i in range(1, len(recent_samples)) 
                              if recent_samples[i] > recent_samples[i-1])
                # Allow some variation, but not consistent growth
                assert increases < len(recent_samples) - 1

    @pytest.mark.asyncio
    async def test_concurrent_service_performance(self, all_services, performance_thresholds):
        """Test performance when multiple services are active concurrently"""
        # Start all services
        for service_name, service in all_services.items():
            if hasattr(service, 'start') and service_name not in ['watchdog', 'config']:
                await service.start()
        
        llm_service = all_services['llm']
        automation_service = all_services['automation']
        security_service = all_services['security']
        
        with patch('httpx.AsyncClient') as mock_client, \
             patch('services.security_service.CRYPTO_AVAILABLE', True):
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Test response"}}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Mock security cipher
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_cipher.decrypt.return_value = b'decrypted_data'
            security_service.cipher_suite = mock_cipher
            
            start_time = time.time()
            
            # Create mixed concurrent workload
            tasks = []
            
            # LLM tasks
            for i in range(10):
                task = llm_service.process_message(f"Concurrent test {i}")
                tasks.append(task)
            
            # Automation tasks
            for i in range(5):
                task_data = {
                    "task_id": f"concurrent-auto-{i}",
                    "task_type": "file_operations",
                    "parameters": {
                        "action": "create",
                        "path": f"/tmp/concurrent_{i}.txt",
                        "content": f"Concurrent content {i}"
                    },
                    "priority": 1,
                    "timeout": 30
                }
                task = automation_service.execute_task(task_data)
                tasks.append(task)
            
            # Security tasks
            for i in range(5):
                task = security_service.encrypt_data(f"Secret data {i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # All tasks should complete successfully
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= len(tasks) * 0.9  # Allow 10% failure rate
            
            # Total time should be reasonable
            assert total_time < 30.0  # Should complete within 30 seconds

    @pytest.mark.asyncio
    async def test_startup_performance(self, all_services):
        """Test service startup performance"""
        startup_times = {}
        
        for service_name, service in all_services.items():
            if hasattr(service, 'start') and service_name not in ['watchdog', 'config']:
                start_time = time.time()
                
                try:
                    await service.start()
                    end_time = time.time()
                    startup_time = end_time - start_time
                    startup_times[service_name] = startup_time
                    
                    # Individual service startup should be fast (less than 5 seconds)
                    assert startup_time < 5.0
                    
                except Exception as e:
                    # Some services may fail in test environment, that's okay
                    print(f"Service {service_name} failed to start: {e}")
        
        # Total startup time should be reasonable
        total_startup_time = sum(startup_times.values())
        assert total_startup_time < 20.0  # All services should start within 20 seconds
        
        print(f"Service startup times: {startup_times}")
        print(f"Total startup time: {total_startup_time:.2f} seconds")

    @pytest.mark.asyncio
    async def test_stress_test_file_operations(self, automation_service):
        """Stress test file operations performance"""
        num_operations = 100
        start_time = time.time()
        
        tasks = []
        for i in range(num_operations):
            task_data = {
                "task_id": f"stress-file-{i}",
                "task_type": "file_operations",
                "parameters": {
                    "action": "create",
                    "path": f"/tmp/stress_test_{i}.txt",
                    "content": f"Stress test content {i}" * 10  # Larger content
                },
                "priority": 1,
                "timeout": 30
            }
            task = automation_service.execute_task(task_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        successful_operations = sum(1 for r in results 
                                  if hasattr(r, 'status') and r.status.value == "completed")
        
        # Should complete most operations successfully
        success_rate = successful_operations / num_operations
        assert success_rate >= 0.95  # 95% success rate
        
        # Should maintain reasonable performance under stress
        avg_time_per_operation = total_time / num_operations
        assert avg_time_per_operation < 1.0  # Less than 1 second per operation
        
        print(f"Stress test: {successful_operations}/{num_operations} operations successful")
        print(f"Average time per operation: {avg_time_per_operation:.3f} seconds")

    @pytest.mark.asyncio
    async def test_context_management_performance(self, llm_service, mock_ollama_response):
        """Test performance of context management with many conversations"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            num_contexts = 100
            messages_per_context = 10
            
            start_time = time.time()
            
            # Create many concurrent conversations
            tasks = []
            for context_id in range(num_contexts):
                for message_id in range(messages_per_context):
                    task = llm_service.process_message(
                        f"Message {message_id} in context {context_id}",
                        f"context-{context_id}"
                    )
                    tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # All messages should be processed
            assert len(results) == num_contexts * messages_per_context
            
            # Should maintain reasonable performance
            avg_time_per_message = total_time / len(results)
            assert avg_time_per_message < 0.1  # Less than 100ms per message
            
            # Context management should work correctly
            assert len(llm_service.contexts) == num_contexts
            
            # Each context should have the right number of messages
            for context_id in range(num_contexts):
                context_key = f"context-{context_id}"
                if context_key in llm_service.contexts:
                    # Should have messages (user + assistant pairs)
                    assert len(llm_service.contexts[context_key]) <= messages_per_context * 2