"""
Comprehensive Security Service for AI Assistant
Handles encryption, sandboxing, permissions, and security monitoring
"""

import asyncio
import logging
import hashlib
import hmac
import secrets
import base64
import json
import time
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import jwt

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class SecurityContext:
    """Security context for operations"""
    def __init__(self, user_id: str, permissions: Set[str], session_id: str):
        self.user_id = user_id
        self.permissions = permissions
        self.session_id = session_id
        self.created_at = time.time()
        self.last_activity = time.time()

class PermissionLevel:
    """Permission levels for operations"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    SYSTEM = "system"

class SecurityService:
    """Comprehensive security service"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Security configuration
        self.master_key: Optional[bytes] = None
        self.encryption_key: Optional[Fernet] = None
        self.jwt_secret: str = secrets.token_urlsafe(32)
        self.session_timeout = 3600  # 1 hour
        
        # Security state
        self.active_sessions: Dict[str, SecurityContext] = {}
        self.failed_attempts: Dict[str, List[float]] = {}
        self.blocked_ips: Set[str] = set()
        self.security_events: List[Dict[str, Any]] = []
        
        # Sandboxing
        self.sandbox_dir = config.get_data_path("sandbox")
        self.sandbox_dir.mkdir(exist_ok=True)
        
        # Permissions
        self.default_permissions = {
            PermissionLevel.READ,
            "file_read",
            "basic_commands"
        }
        
        self.admin_permissions = {
            PermissionLevel.READ,
            PermissionLevel.WRITE,
            PermissionLevel.EXECUTE,
            PermissionLevel.ADMIN,
            "file_read",
            "file_write",
            "file_execute",
            "system_commands",
            "automation",
            "network_access"
        }
        
        # Security policies
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5 minutes
        self.password_min_length = 8
        self.require_2fa = False
        
    async def start(self):
        """Start the security service"""
        try:
            # Initialize encryption
            await self._initialize_encryption()
            
            # Load security configuration
            await self._load_security_config()
            
            # Start security monitoring
            asyncio.create_task(self._security_monitoring_loop())
            
            self.logger.info("Security Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start security service: {e}")
            raise
    
    async def stop(self):
        """Stop the security service"""
        # Clear sensitive data from memory
        self.master_key = None
        self.encryption_key = None
        self.jwt_secret = secrets.token_urlsafe(32)  # Generate new secret
        self.active_sessions.clear()
        
        self.logger.info("Security Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="security_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "encryption_enabled": self.encryption_key is not None,
                    "active_sessions": len(self.active_sessions),
                    "blocked_ips": len(self.blocked_ips),
                    "security_events": len(self.security_events),
                    "sandbox_enabled": self.sandbox_dir.exists(),
                    "2fa_required": self.require_2fa
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="security_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def authenticate_user(self, username: str, password: str, 
                              ip_address: str = "unknown") -> Optional[str]:
        """Authenticate user and return session token"""
        try:
            # Check if IP is blocked
            if ip_address in self.blocked_ips:
                await self._log_security_event("blocked_ip_attempt", {
                    "ip_address": ip_address,
                    "username": username
                })
                return None
            
            # Check failed attempts
            if await self._is_rate_limited(ip_address):
                await self._log_security_event("rate_limit_exceeded", {
                    "ip_address": ip_address,
                    "username": username
                })
                return None
            
            # Verify credentials (simplified - in production, use proper password hashing)
            if await self._verify_credentials(username, password):
                # Create session
                session_id = secrets.token_urlsafe(32)
                permissions = await self._get_user_permissions(username)
                
                context = SecurityContext(
                    user_id=username,
                    permissions=permissions,
                    session_id=session_id
                )
                
                self.active_sessions[session_id] = context
                
                # Generate JWT token
                token = self._generate_jwt_token(username, session_id, permissions)
                
                await self._log_security_event("successful_login", {
                    "username": username,
                    "ip_address": ip_address,
                    "session_id": session_id
                })
                
                # Clear failed attempts
                if ip_address in self.failed_attempts:
                    del self.failed_attempts[ip_address]
                
                return token
            else:
                # Record failed attempt
                await self._record_failed_attempt(ip_address)
                
                await self._log_security_event("failed_login", {
                    "username": username,
                    "ip_address": ip_address
                })
                
                return None
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return None
    
    async def validate_session(self, token: str) -> Optional[SecurityContext]:
        """Validate session token and return security context"""
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            session_id = payload.get('session_id')
            if not session_id or session_id not in self.active_sessions:
                return None
            
            context = self.active_sessions[session_id]
            
            # Check session timeout
            if time.time() - context.last_activity > self.session_timeout:
                await self.invalidate_session(session_id)
                return None
            
            # Update last activity
            context.last_activity = time.time()
            
            return context
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            self.logger.error(f"Session validation error: {e}")
            return None
    
    async def check_permission(self, context: SecurityContext, 
                             permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in context.permissions
    
    async def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            if not self.encryption_key:
                raise Exception("Encryption not initialized")
            
            encrypted_data = self.encryption_key.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            raise
    
    async def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            if not self.encryption_key:
                raise Exception("Encryption not initialized")
            
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.encryption_key.decrypt(encrypted_bytes)
            return decrypted_data.decode()
            
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            raise
    
    async def create_secure_sandbox(self, operation_id: str) -> Path:
        """Create a secure sandbox for operations"""
        try:
            sandbox_path = self.sandbox_dir / f"sandbox_{operation_id}_{int(time.time())}"
            sandbox_path.mkdir(parents=True, exist_ok=True)
            
            # Set restrictive permissions
            os.chmod(sandbox_path, 0o700)
            
            # Create basic structure
            (sandbox_path / "input").mkdir(exist_ok=True)
            (sandbox_path / "output").mkdir(exist_ok=True)
            (sandbox_path / "temp").mkdir(exist_ok=True)
            
            return sandbox_path
            
        except Exception as e:
            self.logger.error(f"Sandbox creation error: {e}")
            raise
    
    async def execute_in_sandbox(self, command: List[str], sandbox_path: Path,
                                timeout: int = 30) -> Dict[str, Any]:
        """Execute command in sandbox with restrictions"""
        try:
            # Security checks
            if not await self._is_command_safe(command):
                raise Exception("Command not allowed")
            
            # Prepare environment
            env = os.environ.copy()
            env['HOME'] = str(sandbox_path)
            env['TMPDIR'] = str(sandbox_path / "temp")
            
            # Execute with restrictions
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=sandbox_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._sandbox_preexec if os.name != 'nt' else None
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    "success": process.returncode == 0,
                    "return_code": process.returncode,
                    "stdout": stdout.decode('utf-8', errors='ignore'),
                    "stderr": stderr.decode('utf-8', errors='ignore')
                }
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise Exception("Command execution timeout")
                
        except Exception as e:
            self.logger.error(f"Sandbox execution error: {e}")
            raise
    
    async def cleanup_sandbox(self, sandbox_path: Path):
        """Clean up sandbox directory"""
        try:
            if sandbox_path.exists() and sandbox_path.is_dir():
                import shutil
                shutil.rmtree(sandbox_path)
                
        except Exception as e:
            self.logger.error(f"Sandbox cleanup error: {e}")
    
    async def scan_for_threats(self, file_path: Path) -> Dict[str, Any]:
        """Scan file for potential threats"""
        try:
            threats = []
            
            # File size check
            if file_path.stat().st_size > 100 * 1024 * 1024:  # 100MB
                threats.append("large_file")
            
            # Extension check
            dangerous_extensions = {'.exe', '.bat', '.cmd', '.scr', '.pif', '.com'}
            if file_path.suffix.lower() in dangerous_extensions:
                threats.append("dangerous_extension")
            
            # Content scan (basic)
            if file_path.is_file():
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read(1024)  # Read first 1KB
                        
                    # Check for suspicious patterns
                    suspicious_patterns = [
                        b'eval(',
                        b'exec(',
                        b'system(',
                        b'shell_exec',
                        b'<script',
                        b'javascript:'
                    ]
                    
                    for pattern in suspicious_patterns:
                        if pattern in content:
                            threats.append(f"suspicious_pattern_{pattern.decode('utf-8', errors='ignore')}")
                            
                except Exception:
                    pass  # File might be binary or inaccessible
            
            return {
                "file_path": str(file_path),
                "threats_found": threats,
                "threat_level": "high" if threats else "low",
                "scan_time": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Threat scan error: {e}")
            return {
                "file_path": str(file_path),
                "threats_found": ["scan_error"],
                "threat_level": "unknown",
                "error": str(e)
            }
    
    async def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        try:
            # Recent security events
            recent_events = [
                event for event in self.security_events
                if time.time() - event['timestamp'] < 86400  # Last 24 hours
            ]
            
            # Event statistics
            event_stats = {}
            for event in recent_events:
                event_type = event['event_type']
                event_stats[event_type] = event_stats.get(event_type, 0) + 1
            
            # Active sessions analysis
            session_stats = {
                "total_sessions": len(self.active_sessions),
                "expired_sessions": 0,
                "active_sessions": 0
            }
            
            current_time = time.time()
            for session in self.active_sessions.values():
                if current_time - session.last_activity > self.session_timeout:
                    session_stats["expired_sessions"] += 1
                else:
                    session_stats["active_sessions"] += 1
            
            return {
                "report_generated": datetime.now().isoformat(),
                "security_events_24h": len(recent_events),
                "event_statistics": event_stats,
                "session_statistics": session_stats,
                "blocked_ips": len(self.blocked_ips),
                "failed_attempts": sum(len(attempts) for attempts in self.failed_attempts.values()),
                "encryption_status": "enabled" if self.encryption_key else "disabled",
                "sandbox_status": "enabled" if self.sandbox_dir.exists() else "disabled",
                "recommendations": await self._generate_security_recommendations()
            }
            
        except Exception as e:
            self.logger.error(f"Security report generation error: {e}")
            return {"error": str(e)}
    
    async def invalidate_session(self, session_id: str):
        """Invalidate a session"""
        if session_id in self.active_sessions:
            context = self.active_sessions[session_id]
            del self.active_sessions[session_id]
            
            await self._log_security_event("session_invalidated", {
                "session_id": session_id,
                "user_id": context.user_id
            })
    
    async def _initialize_encryption(self):
        """Initialize encryption system"""
        try:
            # Generate or load master key
            key_file = self.config.get_data_path("master.key")
            
            if key_file.exists():
                # Load existing key
                with open(key_file, 'rb') as f:
                    self.master_key = f.read()
            else:
                # Generate new key
                self.master_key = Fernet.generate_key()
                
                # Save key securely
                with open(key_file, 'wb') as f:
                    f.write(self.master_key)
                
                # Set restrictive permissions
                os.chmod(key_file, 0o600)
            
            # Initialize Fernet cipher
            self.encryption_key = Fernet(self.master_key)
            
            self.logger.info("Encryption system initialized")
            
        except Exception as e:
            self.logger.error(f"Encryption initialization error: {e}")
            raise
    
    async def _load_security_config(self):
        """Load security configuration"""
        try:
            config_file = self.config.get_data_path("security_config.json")
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    security_config = json.load(f)
                
                self.max_failed_attempts = security_config.get('max_failed_attempts', 5)
                self.lockout_duration = security_config.get('lockout_duration', 300)
                self.session_timeout = security_config.get('session_timeout', 3600)
                self.require_2fa = security_config.get('require_2fa', False)
                
                # Load blocked IPs
                self.blocked_ips = set(security_config.get('blocked_ips', []))
            
        except Exception as e:
            self.logger.error(f"Security config loading error: {e}")
    
    async def _security_monitoring_loop(self):
        """Security monitoring loop"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Clean expired sessions
                await self._cleanup_expired_sessions()
                
                # Clean old failed attempts
                await self._cleanup_failed_attempts()
                
                # Clean old security events
                await self._cleanup_security_events()
                
                # Check for suspicious activity
                await self._detect_suspicious_activity()
                
            except Exception as e:
                self.logger.error(f"Security monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _verify_credentials(self, username: str, password: str) -> bool:
        """Verify user credentials (simplified implementation)"""
        # In production, use proper password hashing (bcrypt, scrypt, etc.)
        # This is a simplified implementation for demonstration
        
        users_file = self.config.get_data_path("users.json")
        
        if not users_file.exists():
            # Create default admin user
            default_users = {
                "admin": {
                    "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
                    "permissions": list(self.admin_permissions),
                    "created_at": time.time()
                }
            }
            
            with open(users_file, 'w') as f:
                json.dump(default_users, f, indent=2)
        
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            if username in users:
                stored_hash = users[username]['password_hash']
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                return hmac.compare_digest(stored_hash, password_hash)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Credential verification error: {e}")
            return False
    
    async def _get_user_permissions(self, username: str) -> Set[str]:
        """Get user permissions"""
        try:
            users_file = self.config.get_data_path("users.json")
            
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            if username in users:
                return set(users[username].get('permissions', list(self.default_permissions)))
            
            return self.default_permissions
            
        except Exception as e:
            self.logger.error(f"Permission retrieval error: {e}")
            return self.default_permissions
    
    def _generate_jwt_token(self, username: str, session_id: str, 
                           permissions: Set[str]) -> str:
        """Generate JWT token"""
        payload = {
            'username': username,
            'session_id': session_id,
            'permissions': list(permissions),
            'iat': time.time(),
            'exp': time.time() + self.session_timeout
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    async def _is_rate_limited(self, ip_address: str) -> bool:
        """Check if IP is rate limited"""
        if ip_address not in self.failed_attempts:
            return False
        
        attempts = self.failed_attempts[ip_address]
        recent_attempts = [
            attempt for attempt in attempts
            if time.time() - attempt < self.lockout_duration
        ]
        
        return len(recent_attempts) >= self.max_failed_attempts
    
    async def _record_failed_attempt(self, ip_address: str):
        """Record failed authentication attempt"""
        if ip_address not in self.failed_attempts:
            self.failed_attempts[ip_address] = []
        
        self.failed_attempts[ip_address].append(time.time())
        
        # Check if should block IP
        recent_attempts = [
            attempt for attempt in self.failed_attempts[ip_address]
            if time.time() - attempt < self.lockout_duration
        ]
        
        if len(recent_attempts) >= self.max_failed_attempts:
            self.blocked_ips.add(ip_address)
            
            await self._log_security_event("ip_blocked", {
                "ip_address": ip_address,
                "failed_attempts": len(recent_attempts)
            })
    
    async def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event"""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details
        }
        
        self.security_events.append(event)
        
        # Keep only recent events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-500:]
        
        # Log to file
        self.logger.warning(f"Security event: {event_type} - {details}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, context in self.active_sessions.items():
            if current_time - context.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.invalidate_session(session_id)
    
    async def _cleanup_failed_attempts(self):
        """Clean up old failed attempts"""
        current_time = time.time()
        
        for ip_address in list(self.failed_attempts.keys()):
            attempts = self.failed_attempts[ip_address]
            recent_attempts = [
                attempt for attempt in attempts
                if current_time - attempt < self.lockout_duration * 2
            ]
            
            if recent_attempts:
                self.failed_attempts[ip_address] = recent_attempts
            else:
                del self.failed_attempts[ip_address]
                
                # Unblock IP if no recent attempts
                if ip_address in self.blocked_ips:
                    self.blocked_ips.remove(ip_address)
    
    async def _cleanup_security_events(self):
        """Clean up old security events"""
        cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days
        
        self.security_events = [
            event for event in self.security_events
            if event['timestamp'] > cutoff_time
        ]
    
    async def _detect_suspicious_activity(self):
        """Detect suspicious activity patterns"""
        try:
            # Check for unusual login patterns
            recent_events = [
                event for event in self.security_events
                if (time.time() - event['timestamp'] < 3600 and  # Last hour
                    event['event_type'] in ['failed_login', 'successful_login'])
            ]
            
            # Multiple failed logins from same IP
            ip_failures = {}
            for event in recent_events:
                if event['event_type'] == 'failed_login':
                    ip = event['details'].get('ip_address', 'unknown')
                    ip_failures[ip] = ip_failures.get(ip, 0) + 1
            
            for ip, failures in ip_failures.items():
                if failures >= 10:  # 10 failures in an hour
                    await self._log_security_event("suspicious_activity", {
                        "type": "multiple_failed_logins",
                        "ip_address": ip,
                        "failure_count": failures
                    })
            
        except Exception as e:
            self.logger.error(f"Suspicious activity detection error: {e}")
    
    async def _is_command_safe(self, command: List[str]) -> bool:
        """Check if command is safe to execute"""
        if not command:
            return False
        
        # Blocked commands
        blocked_commands = {
            'rm', 'del', 'format', 'fdisk', 'mkfs',
            'sudo', 'su', 'chmod', 'chown',
            'wget', 'curl', 'nc', 'netcat',
            'ssh', 'scp', 'rsync'
        }
        
        cmd = command[0].lower()
        if cmd in blocked_commands:
            return False
        
        # Check for dangerous patterns
        command_str = ' '.join(command).lower()
        dangerous_patterns = [
            'rm -rf', 'del /f', '> /dev/', 'format c:',
            '&& rm', '; rm', '| rm', 'eval(',
            'exec(', 'system(', '__import__'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command_str:
                return False
        
        return True
    
    def _sandbox_preexec(self):
        """Preexec function for sandbox (Unix only)"""
        try:
            # Set process group
            os.setpgrp()
            
            # Set resource limits
            import resource
            
            # Limit CPU time (10 seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
            
            # Limit memory (100MB)
            resource.setrlimit(resource.RLIMIT_AS, (100*1024*1024, 100*1024*1024))
            
            # Limit file size (10MB)
            resource.setrlimit(resource.RLIMIT_FSIZE, (10*1024*1024, 10*1024*1024))
            
        except Exception as e:
            # Don't fail if resource limits can't be set
            pass
    
    async def _generate_security_recommendations(self) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        # Check encryption status
        if not self.encryption_key:
            recommendations.append("Enable data encryption for sensitive information")
        
        # Check 2FA status
        if not self.require_2fa:
            recommendations.append("Consider enabling two-factor authentication")
        
        # Check session timeout
        if self.session_timeout > 3600:
            recommendations.append("Consider reducing session timeout for better security")
        
        # Check failed attempts
        if len(self.failed_attempts) > 10:
            recommendations.append("High number of failed login attempts detected - review access logs")
        
        # Check blocked IPs
        if len(self.blocked_ips) > 5:
            recommendations.append("Multiple IPs blocked - consider reviewing security policies")
        
        return recommendations
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security service statistics"""
        return {
            "encryption_enabled": self.encryption_key is not None,
            "active_sessions": len(self.active_sessions),
            "blocked_ips": len(self.blocked_ips),
            "failed_attempts_ips": len(self.failed_attempts),
            "security_events_24h": len([
                e for e in self.security_events
                if time.time() - e['timestamp'] < 86400
            ]),
            "sandbox_enabled": self.sandbox_dir.exists(),
            "2fa_required": self.require_2fa,
            "session_timeout_minutes": self.session_timeout / 60
        }