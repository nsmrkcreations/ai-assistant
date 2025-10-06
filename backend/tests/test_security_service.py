"""
Comprehensive tests for Security Service
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, mock_open
import tempfile
import os
import base64
import secrets
import json
import hashlib
from pathlib import Path

from services.security_service import SecurityService
from models.chat_models import ServiceStatus, SecurityEvent

class TestSecurityService:
    """Test cases for Security Service functionality"""

    @pytest.mark.asyncio
    async def test_service_initialization(self, test_config):
        """Test security service initialization"""
        service = SecurityService(test_config)
        
        assert service.config == test_config
        assert isinstance(service.permissions, dict)
        assert isinstance(service.security_events, list)
        assert isinstance(service.sandbox_processes, dict)

    @pytest.mark.asyncio
    async def test_start_service_with_crypto(self, security_service):
        """Test service startup with cryptography available"""
        with patch('services.security_service.CRYPTO_AVAILABLE', True):
            await security_service.start()
            
            status = await security_service.get_status()
            assert status.name == "security_service"
            assert status.status == ServiceStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_start_service_without_crypto(self, security_service):
        """Test service startup without cryptography"""
        with patch('services.security_service.CRYPTO_AVAILABLE', False):
            await security_service.start()
            
            status = await security_service.get_status()
            assert status.name == "security_service"
            assert status.status == ServiceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_encryption_initialization(self, security_service, temp_dir):
        """Test encryption system initialization"""
        # Create a mock key path that doesn't exist
        key_path = temp_dir / "keys" / "master.key"
        
        with patch('services.security_service.CRYPTO_AVAILABLE', True), \
             patch('services.security_service.Fernet') as mock_fernet, \
             patch.object(security_service.config, 'get_data_path', return_value=key_path), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.chmod'):
            
            mock_key = b'test_key_32_bytes_long_for_testing'
            mock_fernet.generate_key.return_value = mock_key
            mock_cipher = Mock()
            mock_fernet.return_value = mock_cipher
            
            await security_service._init_encryption()
            
            assert security_service.master_key == mock_key
            assert security_service.cipher_suite == mock_cipher

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_data(self, security_service):
        """Test data encryption and decryption"""
        test_data = "Sensitive information to encrypt"
        
        with patch('services.security_service.CRYPTO_AVAILABLE', True):
            # Mock cipher suite
            mock_cipher = Mock()
            encrypted_bytes = b'encrypted_data'
            mock_cipher.encrypt.return_value = encrypted_bytes
            mock_cipher.decrypt.return_value = test_data.encode()
            security_service.cipher_suite = mock_cipher
            
            # Test encryption
            encrypted = await security_service.encrypt_data(test_data)
            assert encrypted == base64.b64encode(encrypted_bytes).decode()
            
            # Test decryption
            decrypted = await security_service.decrypt_data(encrypted)
            assert decrypted == test_data

    @pytest.mark.asyncio
    async def test_encrypt_without_cipher(self, security_service):
        """Test encryption when cipher is not initialized"""
        # Ensure cipher is not initialized
        security_service.cipher_suite = None
        
        with pytest.raises(Exception, match="Encryption not initialized"):
            await security_service.encrypt_data("test data")

    @pytest.mark.asyncio
    async def test_permission_request_basic_allowed(self, security_service):
        """Test permission request for basic allowed operations"""
        user_id = "test_user"
        action = "file_operations"
        resource = "read"
        
        granted = await security_service.request_permission(user_id, action, resource)
        
        assert granted is True
        assert user_id in security_service.permissions
        assert f"{action}:{resource}" in security_service.permissions[user_id]

    @pytest.mark.asyncio
    async def test_permission_request_sensitive_denied(self, security_service):
        """Test permission request for sensitive operations (denied by default)"""
        user_id = "test_user"
        action = "system_admin"
        resource = "root_access"
        
        granted = await security_service.request_permission(user_id, action, resource)
        
        assert granted is False

    @pytest.mark.asyncio
    async def test_permission_request_existing_permission(self, security_service):
        """Test permission request when permission already exists"""
        user_id = "test_user"
        permission = "file_operations:read"
        
        # Grant permission first
        await security_service._grant_permission(user_id, permission)
        
        # Request same permission again
        granted = await security_service.request_permission(user_id, "file_operations", "read")
        
        assert granted is True

    @pytest.mark.asyncio
    async def test_sandboxed_execution_success(self, security_service, temp_dir):
        """Test successful sandboxed script execution"""
        script = "print('Hello from sandbox')"
        permissions = ["file_operations:read"]
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Hello from sandbox\n", b""))
            mock_subprocess.return_value = mock_process
            
            result = await security_service.execute_sandboxed(script, permissions)
            
            assert result["success"] is True
            assert result["return_code"] == 0
            assert "Hello from sandbox" in result["stdout"]

    @pytest.mark.asyncio
    async def test_sandboxed_execution_timeout(self, security_service):
        """Test sandboxed execution with timeout"""
        script = "import time; time.sleep(10)"
        permissions = []
        timeout = 1  # 1 second timeout
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_process.kill = Mock()
            mock_process.wait = AsyncMock()
            mock_subprocess.return_value = mock_process
            
            with pytest.raises(Exception, match="timed out"):
                await security_service.execute_sandboxed(script, permissions, timeout)

    @pytest.mark.asyncio
    async def test_log_security_event(self, security_service):
        """Test logging security events"""
        event_type = "permission_request"
        severity = "medium"
        description = "User requested file access"
        source = "automation_service"
        
        await security_service.log_security_event(event_type, severity, description, source)
        
        assert len(security_service.security_events) == 1
        event = security_service.security_events[0]
        assert event.event_type == event_type
        assert event.severity == severity
        assert event.description == description
        assert event.source == source

    @pytest.mark.asyncio
    async def test_verify_integrity_success(self, security_service, temp_dir):
        """Test file integrity verification (success)"""
        test_file = temp_dir / "test_file.txt"
        test_content = b"Test file content for integrity check"
        test_file.write_bytes(test_content)
        
        # Calculate expected hash
        import hashlib
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        result = await security_service.verify_integrity(str(test_file), expected_hash)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_integrity_failure(self, security_service, temp_dir):
        """Test file integrity verification (failure)"""
        test_file = temp_dir / "test_file.txt"
        test_file.write_bytes(b"Test file content")
        
        wrong_hash = "wrong_hash_value"
        
        result = await security_service.verify_integrity(str(test_file), wrong_hash)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_secure_token(self, security_service):
        """Test secure token generation"""
        token1 = await security_service.generate_secure_token()
        token2 = await security_service.generate_secure_token()
        
        assert len(token1) > 0
        assert len(token2) > 0
        assert token1 != token2  # Should be unique
        
        # Test custom length
        custom_token = await security_service.generate_secure_token(16)
        assert len(custom_token) > 0

    @pytest.mark.asyncio
    async def test_password_hashing_and_verification(self, security_service):
        """Test password hashing and verification"""
        password = "test_password_123"
        
        # Hash password
        hashed, salt = await security_service.hash_password(password)
        
        assert len(hashed) > 0
        assert len(salt) > 0
        
        # Verify correct password
        is_valid = await security_service.verify_password(password, hashed, salt)
        assert is_valid is True
        
        # Verify incorrect password
        is_invalid = await security_service.verify_password("wrong_password", hashed, salt)
        assert is_invalid is False

    @pytest.mark.asyncio
    async def test_load_save_permissions(self, security_service, temp_dir):
        """Test loading and saving permissions"""
        # Mock config path
        security_service.config.get_data_path = Mock(return_value=temp_dir / "permissions.json")
        
        # Add some permissions
        user_id = "test_user"
        permission = "file_operations:read"
        await security_service._grant_permission(user_id, permission)
        
        # Save permissions
        await security_service._save_permissions()
        
        # Clear permissions and reload
        security_service.permissions = {}
        await security_service._load_permissions()
        
        # Verify permissions were loaded
        assert user_id in security_service.permissions
        assert permission in security_service.permissions[user_id]

    @pytest.mark.asyncio
    async def test_revoke_permission(self, security_service):
        """Test revoking user permissions"""
        user_id = "test_user"
        permission = "file_operations:write"
        
        # Grant permission first
        await security_service._grant_permission(user_id, permission)
        assert permission in security_service.permissions[user_id]
        
        # Revoke permission
        await security_service.revoke_permission(user_id, permission)
        assert permission not in security_service.permissions[user_id]

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, security_service):
        """Test getting user permissions"""
        user_id = "test_user"
        permissions = ["file_operations:read", "file_operations:write"]
        
        # Grant permissions
        for permission in permissions:
            await security_service._grant_permission(user_id, permission)
        
        # Get permissions
        user_permissions = await security_service.get_user_permissions(user_id)
        
        assert set(user_permissions) == set(permissions)

    @pytest.mark.asyncio
    async def test_get_user_permissions_nonexistent(self, security_service):
        """Test getting permissions for non-existent user"""
        user_permissions = await security_service.get_user_permissions("nonexistent_user")
        
        assert user_permissions == []

    @pytest.mark.asyncio
    async def test_sandbox_command_creation_unix(self, security_service):
        """Test sandbox command creation on Unix systems"""
        script_path = "/tmp/test_script.py"
        permissions = ["file_operations:read"]
        
        with patch('os.name', 'posix'), \
             patch('subprocess.run') as mock_run:
            
            # Mock firejail availability
            mock_run.return_value.returncode = 0
            
            command = security_service._create_sandbox_command(script_path, permissions)
            
            assert "firejail" in command[0] or "python3" in command[0]

    @pytest.mark.asyncio
    async def test_sandbox_command_creation_windows(self, security_service):
        """Test sandbox command creation on Windows"""
        script_path = "C:\\temp\\test_script.py"
        permissions = ["file_operations:read"]
        
        with patch('os.name', 'nt'):
            command = security_service._create_sandbox_command(script_path, permissions)
            
            assert "python" in command[0]
            assert script_path in command

    @pytest.mark.asyncio
    async def test_security_events_limit(self, security_service):
        """Test security events memory limit"""
        # Clear any existing events
        security_service.security_events.clear()
        
        # Add many security events
        for i in range(1100):  # More than the 1000 limit
            await security_service.log_security_event(
                f"test_event_{i}", "low", f"Test event {i}", "test_source"
            )
        
        # Should be limited to 599 (500 + 99 more events after cleanup)
        # The cleanup happens when we exceed 1000, so we get 500, then add 99 more
        assert len(security_service.security_events) == 599

    @pytest.mark.asyncio
    async def test_get_security_events(self, security_service):
        """Test getting recent security events"""
        # Clear any existing events
        security_service.security_events.clear()
        
        # Add some events
        for i in range(10):
            await security_service.log_security_event(
                f"test_event_{i}", "low", f"Test event {i}", "test_source"
            )
        
        # Get events with limit
        events = await security_service.get_security_events(5)
        
        assert len(events) == 5
        # Should get the most recent events (last 5)
        assert events[0].description == "Test event 5"  # First of the last 5
        assert events[-1].description == "Test event 9"  # Last of the last 5

    @pytest.mark.asyncio
    async def test_clear_security_events(self, security_service, temp_dir):
        """Test clearing security events"""
        # Mock config path
        security_service.config.get_data_path = Mock(return_value=temp_dir / "security_events.json")
        
        # Add some events
        for i in range(5):
            await security_service.log_security_event(
                f"test_event_{i}", "low", f"Test event {i}", "test_source"
            )
        
        assert len(security_service.security_events) == 5
        
        # Clear events
        await security_service.clear_security_events()
        
        assert len(security_service.security_events) == 0

    @pytest.mark.asyncio
    async def test_save_security_events(self, security_service, temp_dir):
        """Test saving security events to file"""
        # Mock config path
        security_service.config.get_data_path = Mock(return_value=temp_dir / "security_events.json")
        
        # Add some events
        for i in range(3):
            await security_service.log_security_event(
                f"test_event_{i}", "medium", f"Test event {i}", "test_source"
            )
        
        # Save events
        await security_service._save_security_events()
        
        # Verify file was created and contains events
        events_file = temp_dir / "security_events.json"
        assert events_file.exists()
        
        with open(events_file, 'r') as f:
            saved_events = json.load(f)
        
        assert len(saved_events) == 3
        assert saved_events[0]["description"] == "Test event 0"

    @pytest.mark.asyncio
    async def test_stop_service_cleanup(self, security_service):
        """Test service cleanup on stop"""
        # Add some sandbox processes
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        security_service.sandbox_processes["test_process"] = mock_process
        
        # Add some security events
        await security_service.log_security_event("test", "low", "test event", "test")
        
        with patch.object(security_service, '_save_security_events') as mock_save:
            await security_service.stop()
            
            # Verify cleanup
            assert len(security_service.sandbox_processes) == 0
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_encryption_error_handling(self, security_service):
        """Test encryption error handling"""
        with patch('services.security_service.CRYPTO_AVAILABLE', True):
            # Mock cipher that raises exception
            mock_cipher = Mock()
            mock_cipher.encrypt.side_effect = Exception("Encryption failed")
            security_service.cipher_suite = mock_cipher
            
            with pytest.raises(Exception):
                await security_service.encrypt_data("test data")

    @pytest.mark.asyncio
    async def test_permission_error_handling(self, security_service):
        """Test permission request error handling"""
        with patch.object(security_service, '_grant_permission', side_effect=Exception("Permission error")):
            granted = await security_service.request_permission("user", "file_operations", "read")
            
            assert granted is False

    @pytest.mark.asyncio
    async def test_sandbox_process_cleanup(self, security_service):
        """Test sandbox process cleanup"""
        # Add mock processes
        mock_process1 = Mock()
        mock_process1.terminate = Mock()
        mock_process1.wait = Mock()
        
        mock_process2 = Mock()
        mock_process2.terminate = Mock()
        mock_process2.wait = Mock(side_effect=Exception("Process error"))
        mock_process2.kill = Mock()
        
        security_service.sandbox_processes["process1"] = mock_process1
        security_service.sandbox_processes["process2"] = mock_process2
        
        await security_service.stop()
        
        # Verify all processes were handled
        mock_process1.terminate.assert_called_once()
        mock_process2.terminate.assert_called_once()
        assert len(security_service.sandbox_processes) == 0

    @pytest.mark.asyncio
    async def test_file_integrity_error_handling(self, security_service):
        """Test file integrity verification error handling"""
        # Test with non-existent file
        result = await security_service.verify_integrity("/nonexistent/file.txt", "hash")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_password_verification_error_handling(self, security_service):
        """Test password verification error handling"""
        # Test with invalid base64 data
        result = await security_service.verify_password("password", "invalid_hash", "invalid_salt")
        
        assert result is False