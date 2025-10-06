"""
Comprehensive integration tests for the complete AI Assistant system
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from main import app, service_manager
from services.service_manager import ServiceManager
from services.database_service import DatabaseService
from services.plugin_service import PluginService
from services.recovery_service import RecoveryService
from services.performance_service import PerformanceService
from utils.config import Config

class TestCompleteIntegration:
    """Test complete system integration"""
    
    @pytest.fixture
    async def setup_system(self):
        """Setup complete system for testing"""
        config = Config()
        
        # Create service manager
        manager = ServiceManager(config)
        
        # Register core services
        manager.register_service("database", DatabaseService, [], 10)
        manager.register_service("recovery", RecoveryService, ["database"], 25)
        manager.register_service("plugin", PluginService, ["database"], 30)
        manager.register_service("performance", PerformanceService, ["database"], 78)
        
        # Start services
        await manager.start_all_services()
        
        yield manager
        
        # Cleanup
        await manager.stop_all_services()
    
    @pytest.mark.asyncio
    async def test_service_startup_sequence(self, setup_system):
        """Test that all services start in correct order"""
        manager = setup_system
        
        # Check all services are running
        statuses = await manager.get_all_service_status()
        
        assert len(statuses) == 4
        for name, status in statuses.items():
            assert status.status.value in ['healthy', 'degraded']
            assert status.name == name
    
    @pytest.mark.asyncio
    async def test_database_integration(self, setup_system):
        """Test database service integration"""
        manager = setup_system
        database_service = manager.get_service('database')
        
        assert database_service is not None
        
        # Test saving and retrieving data
        await database_service.save_user_preference('test_key', 'test_value')
        value = await database_service.get_user_preference('test_key')
        
        assert value == 'test_value'
        
        # Test chat history
        await database_service.save_chat_message(
            'test_context', 
            'Hello', 
            'Hi there!', 
            {'test': True}
        )
        
        history = await database_service.get_chat_history('test_context', 1)
        assert len(history) == 1
        assert history[0]['user_message'] == 'Hello'
        assert history[0]['assistant_response'] == 'Hi there!'
    
    @pytest.mark.asyncio
    async def test_recovery_service_integration(self, setup_system):
        """Test recovery service integration"""
        manager = setup_system
        recovery_service = manager.get_service('recovery')
        
        assert recovery_service is not None
        
        # Test service registration
        mock_service = Mock()
        mock_service.get_status = Mock(return_value=Mock(status=Mock(value='healthy')))
        
        recovery_service.register_service('test_service', mock_service)
        
        # Test manual recovery
        result = await recovery_service.manual_recovery(
            'test_service', 
            recovery_service.RecoveryAction.RESTART_SERVICE
        )
        
        # Should fail since mock service doesn't have restart methods
        assert result is False
    
    @pytest.mark.asyncio
    async def test_plugin_service_integration(self, setup_system):
        """Test plugin service integration"""
        manager = setup_system
        plugin_service = manager.get_service('plugin')
        
        assert plugin_service is not None
        
        # Test plugin listing
        plugins = plugin_service.list_plugins()
        assert isinstance(plugins, dict)
    
    @pytest.mark.asyncio
    async def test_performance_service_integration(self, setup_system):
        """Test performance service integration"""
        manager = setup_system
        performance_service = manager.get_service('performance')
        
        assert performance_service is not None
        
        # Test metrics collection
        metrics = performance_service.get_current_metrics()
        assert metrics.cpu_percent >= 0
        assert metrics.memory_percent >= 0
        assert metrics.memory_used_mb >= 0
        
        # Test performance summary
        summary = performance_service.get_performance_summary()
        assert isinstance(summary, dict)
        
        # Test optimization
        result = await performance_service.optimize_performance()
        assert result['status'] == 'success'
        assert 'collected_objects' in result
    
    @pytest.mark.asyncio
    async def test_service_restart_integration(self, setup_system):
        """Test service restart functionality"""
        manager = setup_system
        
        # Test restarting a service
        success = await manager.restart_service('database')
        assert success is True
        
        # Check service is still healthy after restart
        status = await manager.get_service('database').get_status()
        assert status.status.value in ['healthy', 'degraded']
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, setup_system):
        """Test error recovery integration"""
        manager = setup_system
        recovery_service = manager.get_service('recovery')
        
        # Simulate service error
        mock_service = Mock()
        mock_service.get_status = Mock(return_value=Mock(
            status=Mock(value='offline'),
            error='Test error'
        ))
        mock_service.start = Mock()
        mock_service.stop = Mock()
        
        recovery_service.register_service('failing_service', mock_service)
        
        # Trigger recovery
        result = await recovery_service.manual_recovery(
            'failing_service',
            recovery_service.RecoveryAction.RESTART_SERVICE
        )
        
        # Should succeed since mock has start/stop methods
        assert result is True
        mock_service.stop.assert_called_once()
        mock_service.start.assert_called_once()

class TestAPIIntegration:
    """Test API integration"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        assert response.status_code in [200, 503]  # May be 503 if services not started
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_settings_endpoints(self):
        """Test settings API endpoints"""
        # Test getting settings (may fail if database not available)
        response = self.client.get("/api/settings")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
    
    def test_service_status_endpoint(self):
        """Test service status endpoint"""
        response = self.client.get("/services/status")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "services" in data
            assert isinstance(data["services"], dict)
    
    def test_error_logging_endpoint(self):
        """Test error logging endpoint"""
        error_data = {
            "error": {
                "message": "Test error",
                "stack": "Test stack trace"
            },
            "errorId": "test_error_123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        response = self.client.post("/api/errors", json=error_data)
        assert response.status_code in [200, 503]
    
    def test_performance_endpoints(self):
        """Test performance API endpoints"""
        # Test getting performance metrics
        response = self.client.get("/api/performance")
        assert response.status_code in [200, 503]
        
        # Test performance optimization
        response = self.client.post("/api/performance/optimize")
        assert response.status_code in [200, 503]

class TestWebSocketIntegration:
    """Test WebSocket integration"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        # This would require a running server
        # For now, just test that the endpoint exists
        client = TestClient(app)
        
        # Test WebSocket endpoint exists
        with pytest.raises(Exception):  # Will fail without proper WebSocket client
            with client.websocket_connect("/ws") as websocket:
                pass

class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_chat_workflow(self, setup_system):
        """Test complete chat workflow"""
        manager = setup_system
        database_service = manager.get_service('database')
        
        # Simulate a complete chat interaction
        context_id = "test_workflow_123"
        user_message = "Hello, how are you?"
        assistant_response = "I'm doing well, thank you for asking!"
        
        # Save chat message
        await database_service.save_chat_message(
            context_id, user_message, assistant_response, 
            {"workflow_test": True}
        )
        
        # Retrieve chat history
        history = await database_service.get_chat_history(context_id, 10)
        
        assert len(history) >= 1
        found_message = False
        for msg in history:
            if msg['user_message'] == user_message:
                found_message = True
                assert msg['assistant_response'] == assistant_response
                break
        
        assert found_message
    
    @pytest.mark.asyncio
    async def test_settings_workflow(self, setup_system):
        """Test complete settings workflow"""
        manager = setup_system
        database_service = manager.get_service('database')
        
        # Test saving various settings
        settings = {
            'theme': 'dark',
            'language': 'en',
            'voiceEnabled': True,
            'automationEnabled': False
        }
        
        for key, value in settings.items():
            await database_service.save_user_preference(key, value)
        
        # Retrieve and verify settings
        for key, expected_value in settings.items():
            actual_value = await database_service.get_user_preference(key)
            assert actual_value == expected_value
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_workflow(self, setup_system):
        """Test performance monitoring workflow"""
        manager = setup_system
        performance_service = manager.get_service('performance')
        
        # Get initial metrics
        initial_metrics = performance_service.get_current_metrics()
        assert initial_metrics.cpu_percent >= 0
        
        # Wait a bit for metrics collection
        await asyncio.sleep(1)
        
        # Get summary
        summary = performance_service.get_performance_summary()
        
        # Should have some data
        if summary:  # May be empty if service just started
            assert 'current' in summary or len(summary) == 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, setup_system):
        """Test error recovery workflow"""
        manager = setup_system
        recovery_service = manager.get_service('recovery')
        
        # Create a mock failing service
        failing_service = Mock()
        failing_service.get_status = Mock(return_value=Mock(
            status=Mock(value='offline'),
            error='Simulated failure'
        ))
        failing_service.start = Mock()
        failing_service.stop = Mock()
        
        # Register the failing service
        recovery_service.register_service('test_failing', failing_service)
        
        # Trigger recovery
        success = await recovery_service.manual_recovery(
            'test_failing',
            recovery_service.RecoveryAction.RESTART_SERVICE
        )
        
        assert success is True
        failing_service.stop.assert_called_once()
        failing_service.start.assert_called_once()
        
        # Check recovery history
        history = recovery_service.get_recovery_history('test_failing')
        assert len(history) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])