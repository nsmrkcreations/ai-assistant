"""
Database Service for persistent data storage
"""

import asyncio
import logging
import sqlite3
import json
import aiosqlite
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class DatabaseService:
    """Database service for persistent storage"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_path = None
        self.connection = None
        
    async def start(self):
        """Start the database service"""
        try:
            # Create database directory
            db_dir = self.config.get_data_path("database")
            db_dir.mkdir(parents=True, exist_ok=True)
            
            self.db_path = db_dir / "ai_assistant.db"
            
            # Initialize database
            await self._initialize_database()
            
            self.logger.info("Database Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start Database service: {e}")
            raise
    
    async def stop(self):
        """Stop the database service"""
        if self.connection:
            await self.connection.close()
        self.logger.info("Database Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            if self.db_path and self.db_path.exists():
                return ComponentStatus(
                    name="database_service",
                    status=ServiceStatus.HEALTHY,
                    details={
                        "database_path": str(self.db_path),
                        "database_size": self.db_path.stat().st_size if self.db_path.exists() else 0
                    }
                )
            else:
                return ComponentStatus(
                    name="database_service",
                    status=ServiceStatus.DEGRADED,
                    error="Database file not found"
                )
                
        except Exception as e:
            return ComponentStatus(
                name="database_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def _initialize_database(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Chat history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT,
                    user_message TEXT,
                    assistant_response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # User preferences table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Automation history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    task_type TEXT,
                    parameters TEXT,
                    result TEXT,
                    status TEXT,
                    execution_time REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Learning data table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS learning_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interaction_type TEXT,
                    input_data TEXT,
                    output_data TEXT,
                    feedback_score REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    service TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
    
    async def save_chat_message(self, context_id: str, user_message: str, 
                               assistant_response: str, metadata: Dict = None):
        """Save chat message to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO chat_history (context_id, user_message, assistant_response, metadata)
                    VALUES (?, ?, ?, ?)
                """, (context_id, user_message, assistant_response, json.dumps(metadata or {})))
                await db.commit()
        except Exception as e:
            self.logger.error(f"Failed to save chat message: {e}")
    
    async def get_chat_history(self, context_id: str = None, limit: int = 50) -> List[Dict]:
        """Get chat history"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if context_id:
                    cursor = await db.execute("""
                        SELECT * FROM chat_history 
                        WHERE context_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (context_id, limit))
                else:
                    cursor = await db.execute("""
                        SELECT * FROM chat_history 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (limit,))
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get chat history: {e}")
            return []
    
    async def save_user_preference(self, key: str, value: Any):
        """Save user preference"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(value)))
                await db.commit()
        except Exception as e:
            self.logger.error(f"Failed to save user preference: {e}")
    
    async def get_user_preference(self, key: str, default=None):
        """Get user preference"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT value FROM user_preferences WHERE key = ?
                """, (key,))
                row = await cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                return default
        except Exception as e:
            self.logger.error(f"Failed to get user preference: {e}")
            return default
    
    async def save_automation_result(self, task_id: str, task_type: str, 
                                   parameters: Dict, result: Dict, status: str, 
                                   execution_time: float):
        """Save automation task result"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO automation_history 
                    (task_id, task_type, parameters, result, status, execution_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, task_type, json.dumps(parameters), 
                     json.dumps(result), status, execution_time))
                await db.commit()
        except Exception as e:
            self.logger.error(f"Failed to save automation result: {e}")
    
    async def save_learning_data(self, interaction_type: str, input_data: Dict, 
                               output_data: Dict, feedback_score: float = None):
        """Save learning interaction data"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO learning_data 
                    (interaction_type, input_data, output_data, feedback_score)
                    VALUES (?, ?, ?, ?)
                """, (interaction_type, json.dumps(input_data), 
                     json.dumps(output_data), feedback_score))
                await db.commit()
        except Exception as e:
            self.logger.error(f"Failed to save learning data: {e}")
    
    async def log_system_event(self, level: str, service: str, message: str):
        """Log system event"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO system_logs (level, service, message)
                    VALUES (?, ?, ?)
                """, (level, service, message))
                await db.commit()
        except Exception as e:
            self.logger.error(f"Failed to log system event: {e}")
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old data"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Clean up old chat history
                await db.execute("""
                    DELETE FROM chat_history 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days))
                
                # Clean up old automation history
                await db.execute("""
                    DELETE FROM automation_history 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days))
                
                # Clean up old system logs
                await db.execute("""
                    DELETE FROM system_logs 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days))
                
                await db.commit()
                self.logger.info(f"Cleaned up data older than {days} days")
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")