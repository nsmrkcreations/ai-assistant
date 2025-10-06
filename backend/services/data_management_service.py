"""
Data Management and Privacy Controls Service for AI Assistant
Handles data storage, privacy controls, GDPR compliance, and user data management
"""

import asyncio
import logging
import json
import time
import hashlib
import shutil
import sqlite3
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import zipfile
import tempfile

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class DataCategory(Enum):
    """Data categories for privacy management"""
    PERSONAL = "personal"
    CONVERSATION = "conversation"
    USAGE = "usage"
    SYSTEM = "system"
    TEMPORARY = "temporary"
    ANALYTICS = "analytics"

class RetentionPolicy(Enum):
    """Data retention policies"""
    IMMEDIATE = "immediate"  # Delete immediately
    SHORT = "short"         # 7 days
    MEDIUM = "medium"       # 30 days
    LONG = "long"          # 1 year
    PERMANENT = "permanent" # Keep indefinitely

@dataclass
class DataRecord:
    """Represents a data record with privacy metadata"""
    record_id: str
    category: DataCategory
    data_type: str
    created_at: float
    last_accessed: float
    retention_policy: RetentionPolicy
    encrypted: bool
    user_consent: bool
    metadata: Dict[str, Any]

@dataclass
class PrivacySettings:
    """User privacy settings"""
    data_collection_enabled: bool = True
    analytics_enabled: bool = False
    conversation_logging: bool = True
    usage_tracking: bool = True
    data_sharing: bool = False
    retention_preferences: Dict[str, str] = Nonecla
ss DataManagementService:
    """Service for data management and privacy controls"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Database and storage
        self.db_path = config.get_data_path("data_management.db")
        self.data_dir = config.get_data_path("user_data")
        self.exports_dir = config.get_data_path("exports")
        self.backups_dir = config.get_data_path("backups")
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)
        
        # Privacy settings
        self.privacy_settings = PrivacySettings()
        
        # Data tracking
        self.data_records: Dict[str, DataRecord] = {}
        self.retention_policies = {
            DataCategory.PERSONAL: RetentionPolicy.PERMANENT,
            DataCategory.CONVERSATION: RetentionPolicy.LONG,
            DataCategory.USAGE: RetentionPolicy.MEDIUM,
            DataCategory.SYSTEM: RetentionPolicy.LONG,
            DataCategory.TEMPORARY: RetentionPolicy.IMMEDIATE,
            DataCategory.ANALYTICS: RetentionPolicy.SHORT
        }
        
        # Cleanup intervals
        self.cleanup_interval = 3600  # 1 hour
        
    async def start(self):
        """Start the data management service"""
        try:
            # Initialize database
            await self._initialize_database()
            
            # Load privacy settings
            await self._load_privacy_settings()
            
            # Load data records
            await self._load_data_records()
            
            # Start cleanup loop
            asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("Data Management Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start data management service: {e}")
            raise
    
    async def stop(self):
        """Stop the data management service"""
        # Save current state
        await self._save_privacy_settings()
        await self._save_data_records()
        
        self.logger.info("Data Management Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="data_management_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "data_records": len(self.data_records),
                    "privacy_settings_loaded": self.privacy_settings is not None,
                    "database_size": self._get_database_size(),
                    "data_directory_size": self._get_directory_size(self.data_dir),
                    "gdpr_compliant": await self._check_gdpr_compliance()
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="data_management_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def store_data(self, data_type: str, data: Any, category: DataCategory,
                        user_consent: bool = True, encrypt: bool = False) -> str:
        """Store data with privacy controls"""
        try:
            # Check if data collection is enabled
            if not self.privacy_settings.data_collection_enabled and category != DataCategory.SYSTEM:
                raise Exception("Data collection is disabled")
            
            # Generate record ID
            record_id = hashlib.sha256(f"{data_type}_{time.time()}".encode()).hexdigest()[:16]
            
            # Create data record
            record = DataRecord(
                record_id=record_id,
                category=category,
                data_type=data_type,
                created_at=time.time(),
                last_accessed=time.time(),
                retention_policy=self.retention_policies.get(category, RetentionPolicy.MEDIUM),
                encrypted=encrypt,
                user_consent=user_consent,
                metadata={}
            )
            
            # Store data
            data_file = self.data_dir / f"{record_id}.json"
            
            if encrypt:
                # Encrypt data (requires security service)
                encrypted_data = await self._encrypt_data(json.dumps(data))
                with open(data_file, 'w') as f:
                    json.dump({"encrypted": True, "data": encrypted_data}, f)
            else:
                with open(data_file, 'w') as f:
                    json.dump({"encrypted": False, "data": data}, f)
            
            # Store record metadata
            self.data_records[record_id] = record
            await self._store_record_in_db(record)
            
            return record_id
            
        except Exception as e:
            self.logger.error(f"Error storing data: {e}")
            raise
    
    async def retrieve_data(self, record_id: str) -> Optional[Any]:
        """Retrieve data by record ID"""
        try:
            if record_id not in self.data_records:
                return None
            
            record = self.data_records[record_id]
            
            # Update last accessed time
            record.last_accessed = time.time()
            await self._update_record_in_db(record)
            
            # Load data
            data_file = self.data_dir / f"{record_id}.json"
            if not data_file.exists():
                return None
            
            with open(data_file, 'r') as f:
                stored_data = json.load(f)
            
            if stored_data.get("encrypted", False):
                # Decrypt data
                decrypted_data = await self._decrypt_data(stored_data["data"])
                return json.loads(decrypted_data)
            else:
                return stored_data["data"]
                
        except Exception as e:
            self.logger.error(f"Error retrieving data: {e}")
            return None
    
    async def delete_data(self, record_id: str, reason: str = "user_request") -> bool:
        """Delete data record"""
        try:
            if record_id not in self.data_records:
                return False
            
            record = self.data_records[record_id]
            
            # Delete data file
            data_file = self.data_dir / f"{record_id}.json"
            if data_file.exists():
                data_file.unlink()
            
            # Remove from database
            await self._delete_record_from_db(record_id)
            
            # Remove from memory
            del self.data_records[record_id]
            
            # Log deletion
            await self._log_data_action("delete", record_id, reason)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting data: {e}")
            return False
    
    async def update_privacy_settings(self, settings: Dict[str, Any]) -> bool:
        """Update user privacy settings"""
        try:
            # Update settings
            for key, value in settings.items():
                if hasattr(self.privacy_settings, key):
                    setattr(self.privacy_settings, key, value)
            
            # Save settings
            await self._save_privacy_settings()
            
            # Apply settings retroactively if needed
            await self._apply_privacy_settings()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating privacy settings: {e}")
            return False
    
    async def export_user_data(self, categories: Optional[List[DataCategory]] = None) -> str:
        """Export user data (GDPR compliance)"""
        try:
            # Create export directory
            export_id = f"export_{int(time.time())}"
            export_path = self.exports_dir / export_id
            export_path.mkdir(exist_ok=True)
            
            # Filter records by categories
            records_to_export = []
            for record in self.data_records.values():
                if categories is None or record.category in categories:
                    if record.user_consent:  # Only export consented data
                        records_to_export.append(record)
            
            # Export data
            exported_data = {
                "export_info": {
                    "export_id": export_id,
                    "created_at": datetime.now().isoformat(),
                    "categories": [cat.value for cat in categories] if categories else "all",
                    "record_count": len(records_to_export)
                },
                "privacy_settings": asdict(self.privacy_settings),
                "data_records": []
            }
            
            for record in records_to_export:
                # Retrieve data
                data = await self.retrieve_data(record.record_id)
                
                exported_record = {
                    "record_info": asdict(record),
                    "data": data
                }
                
                exported_data["data_records"].append(exported_record)
            
            # Save export
            export_file = export_path / "user_data_export.json"
            with open(export_file, 'w') as f:
                json.dump(exported_data, f, indent=2, default=str)
            
            # Create ZIP archive
            zip_file = self.exports_dir / f"{export_id}.zip"
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(export_file, "user_data_export.json")
            
            # Clean up temporary directory
            shutil.rmtree(export_path)
            
            # Log export
            await self._log_data_action("export", export_id, f"categories: {categories}")
            
            return str(zip_file)
            
        except Exception as e:
            self.logger.error(f"Error exporting user data: {e}")
            raise
    
    async def delete_all_user_data(self, confirmation_code: str) -> bool:
        """Delete all user data (GDPR right to be forgotten)"""
        try:
            # Verify confirmation code
            expected_code = hashlib.sha256(f"delete_all_{int(time.time() // 3600)}".encode()).hexdigest()[:8]
            if confirmation_code != expected_code:
                raise Exception("Invalid confirmation code")
            
            # Get all user data records (excluding system data)
            user_records = [
                record_id for record_id, record in self.data_records.items()
                if record.category != DataCategory.SYSTEM
            ]
            
            # Delete all user data
            deleted_count = 0
            for record_id in user_records:
                if await self.delete_data(record_id, "user_requested_deletion"):
                    deleted_count += 1
            
            # Log mass deletion
            await self._log_data_action("mass_delete", "all_user_data", f"deleted {deleted_count} records")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting all user data: {e}")
            return False
    
    async def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of stored data"""
        try:
            summary = {
                "total_records": len(self.data_records),
                "categories": {},
                "retention_policies": {},
                "encrypted_records": 0,
                "consented_records": 0,
                "storage_size_mb": self._get_directory_size(self.data_dir) / (1024 * 1024)
            }
            
            for record in self.data_records.values():
                # Count by category
                category = record.category.value
                summary["categories"][category] = summary["categories"].get(category, 0) + 1
                
                # Count by retention policy
                policy = record.retention_policy.value
                summary["retention_policies"][policy] = summary["retention_policies"].get(policy, 0) + 1
                
                # Count encrypted and consented
                if record.encrypted:
                    summary["encrypted_records"] += 1
                if record.user_consent:
                    summary["consented_records"] += 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting data summary: {e}")
            return {}
    
    async def _cleanup_loop(self):
        """Data cleanup loop based on retention policies"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_data()
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _cleanup_expired_data(self):
        """Clean up expired data based on retention policies"""
        try:
            current_time = time.time()
            expired_records = []
            
            for record_id, record in self.data_records.items():
                # Calculate expiry time based on retention policy
                if record.retention_policy == RetentionPolicy.IMMEDIATE:
                    expiry_time = record.created_at
                elif record.retention_policy == RetentionPolicy.SHORT:
                    expiry_time = record.created_at + (7 * 24 * 3600)  # 7 days
                elif record.retention_policy == RetentionPolicy.MEDIUM:
                    expiry_time = record.created_at + (30 * 24 * 3600)  # 30 days
                elif record.retention_policy == RetentionPolicy.LONG:
                    expiry_time = record.created_at + (365 * 24 * 3600)  # 1 year
                else:  # PERMANENT
                    continue
                
                if current_time > expiry_time:
                    expired_records.append(record_id)
            
            # Delete expired records
            for record_id in expired_records:
                await self.delete_data(record_id, "retention_policy_expired")
            
            if expired_records:
                self.logger.info(f"Cleaned up {len(expired_records)} expired data records")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up expired data: {e}")
    
    async def _initialize_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_records (
                    record_id TEXT PRIMARY KEY,
                    category TEXT,
                    data_type TEXT,
                    created_at REAL,
                    last_accessed REAL,
                    retention_policy TEXT,
                    encrypted BOOLEAN,
                    user_consent BOOLEAN,
                    metadata TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    action_type TEXT,
                    record_id TEXT,
                    reason TEXT,
                    details TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_category ON data_records(category)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_created_at ON data_records(created_at)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    async def _load_privacy_settings(self):
        """Load privacy settings from file"""
        try:
            settings_file = self.config.get_data_path("privacy_settings.json")
            
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings_data = json.load(f)
                
                self.privacy_settings = PrivacySettings(**settings_data)
            
        except Exception as e:
            self.logger.error(f"Error loading privacy settings: {e}")
    
    async def _save_privacy_settings(self):
        """Save privacy settings to file"""
        try:
            settings_file = self.config.get_data_path("privacy_settings.json")
            
            with open(settings_file, 'w') as f:
                json.dump(asdict(self.privacy_settings), f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error saving privacy settings: {e}")
    
    async def _load_data_records(self):
        """Load data records from database"""
        try:
            if not self.db_path.exists():
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM data_records')
            rows = cursor.fetchall()
            
            for row in rows:
                record = DataRecord(
                    record_id=row[0],
                    category=DataCategory(row[1]),
                    data_type=row[2],
                    created_at=row[3],
                    last_accessed=row[4],
                    retention_policy=RetentionPolicy(row[5]),
                    encrypted=bool(row[6]),
                    user_consent=bool(row[7]),
                    metadata=json.loads(row[8]) if row[8] else {}
                )
                
                self.data_records[record.record_id] = record
            
            conn.close()
            
            self.logger.info(f"Loaded {len(self.data_records)} data records")
            
        except Exception as e:
            self.logger.error(f"Error loading data records: {e}")
    
    async def _save_data_records(self):
        """Save data records to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing records
            cursor.execute('DELETE FROM data_records')
            
            # Insert current records
            for record in self.data_records.values():
                cursor.execute('''
                    INSERT INTO data_records 
                    (record_id, category, data_type, created_at, last_accessed, 
                     retention_policy, encrypted, user_consent, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.record_id,
                    record.category.value,
                    record.data_type,
                    record.created_at,
                    record.last_accessed,
                    record.retention_policy.value,
                    record.encrypted,
                    record.user_consent,
                    json.dumps(record.metadata)
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving data records: {e}")
    
    async def _store_record_in_db(self, record: DataRecord):
        """Store single record in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO data_records 
                (record_id, category, data_type, created_at, last_accessed, 
                 retention_policy, encrypted, user_consent, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.record_id,
                record.category.value,
                record.data_type,
                record.created_at,
                record.last_accessed,
                record.retention_policy.value,
                record.encrypted,
                record.user_consent,
                json.dumps(record.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing record in database: {e}")
    
    async def _update_record_in_db(self, record: DataRecord):
        """Update record in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE data_records 
                SET last_accessed = ?, metadata = ?
                WHERE record_id = ?
            ''', (
                record.last_accessed,
                json.dumps(record.metadata),
                record.record_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error updating record in database: {e}")
    
    async def _delete_record_from_db(self, record_id: str):
        """Delete record from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM data_records WHERE record_id = ?', (record_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error deleting record from database: {e}")
    
    async def _log_data_action(self, action_type: str, record_id: str, reason: str):
        """Log data action for audit trail"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO data_actions 
                (timestamp, action_type, record_id, reason, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                time.time(),
                action_type,
                record_id,
                reason,
                ""
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error logging data action: {e}")
    
    async def _apply_privacy_settings(self):
        """Apply privacy settings retroactively"""
        try:
            # If data collection is disabled, mark for deletion
            if not self.privacy_settings.data_collection_enabled:
                for record_id, record in list(self.data_records.items()):
                    if record.category not in [DataCategory.SYSTEM]:
                        await self.delete_data(record_id, "data_collection_disabled")
            
            # If analytics disabled, delete analytics data
            if not self.privacy_settings.analytics_enabled:
                for record_id, record in list(self.data_records.items()):
                    if record.category == DataCategory.ANALYTICS:
                        await self.delete_data(record_id, "analytics_disabled")
            
            # If conversation logging disabled, delete conversation data
            if not self.privacy_settings.conversation_logging:
                for record_id, record in list(self.data_records.items()):
                    if record.category == DataCategory.CONVERSATION:
                        await self.delete_data(record_id, "conversation_logging_disabled")
            
        except Exception as e:
            self.logger.error(f"Error applying privacy settings: {e}")
    
    async def _encrypt_data(self, data: str) -> str:
        """Encrypt data (placeholder - would use security service)"""
        # This would integrate with the security service for actual encryption
        return base64.b64encode(data.encode()).decode()
    
    async def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data (placeholder - would use security service)"""
        # This would integrate with the security service for actual decryption
        return base64.b64decode(encrypted_data.encode()).decode()
    
    def _get_database_size(self) -> int:
        """Get database file size in bytes"""
        try:
            if self.db_path.exists():
                return self.db_path.stat().st_size
            return 0
        except:
            return 0
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get directory size in bytes"""
        try:
            total_size = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except:
            return 0
    
    async def _check_gdpr_compliance(self) -> bool:
        """Check GDPR compliance status"""
        try:
            # Check if privacy settings are properly configured
            if not hasattr(self.privacy_settings, 'data_collection_enabled'):
                return False
            
            # Check if user consent is tracked
            consented_records = sum(1 for record in self.data_records.values() if record.user_consent)
            total_records = len(self.data_records)
            
            # Should have high percentage of consented records
            if total_records > 0 and (consented_records / total_records) < 0.8:
                return False
            
            # Check if retention policies are set
            for record in self.data_records.values():
                if record.retention_policy == RetentionPolicy.PERMANENT and record.category != DataCategory.SYSTEM:
                    # Non-system data shouldn't be permanent without explicit consent
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking GDPR compliance: {e}")
            return False
    
    def get_data_management_stats(self) -> Dict[str, Any]:
        """Get data management statistics"""
        return {
            "total_records": len(self.data_records),
            "categories": {cat.value: len([r for r in self.data_records.values() if r.category == cat]) 
                          for cat in DataCategory},
            "encrypted_records": len([r for r in self.data_records.values() if r.encrypted]),
            "consented_records": len([r for r in self.data_records.values() if r.user_consent]),
            "database_size_mb": self._get_database_size() / (1024 * 1024),
            "data_directory_size_mb": self._get_directory_size(self.data_dir) / (1024 * 1024),
            "privacy_settings": asdict(self.privacy_settings),
            "gdpr_compliant": await self._check_gdpr_compliance()
        }