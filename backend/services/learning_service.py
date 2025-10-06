"""
Learning and Personalization Service for AI Assistant
Learns user patterns, preferences, and provides personalized assistance
"""

import asyncio
import logging
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sqlite3
import numpy as np
from dataclasses import dataclass, asdict
import pickle

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

@dataclass
class UserAction:
    """Represents a user action for learning"""
    timestamp: float
    action_type: str  # 'command', 'file_access', 'app_usage', 'voice_input', etc.
    context: Dict[str, Any]
    success: bool
    duration: float = 0.0
    metadata: Dict[str, Any] = None

@dataclass
class UserPattern:
    """Represents a learned user pattern"""
    pattern_id: str
    pattern_type: str  # 'temporal', 'sequential', 'contextual'
    confidence: float
    frequency: int
    last_seen: float
    description: str
    triggers: List[str]
    suggestions: List[str]

@dataclass
class UserPreference:
    """Represents a user preference"""
    key: str
    value: Any
    confidence: float
    learned_from: List[str]  # Sources that contributed to this preference
    last_updated: float

class LearningService:
    """Service for learning user patterns and personalizing experience"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Database and storage
        self.db_path = config.get_data_path("learning.db")
        self.patterns_file = config.get_data_path("patterns.json")
        self.preferences_file = config.get_data_path("preferences.json")
        
        # Learning parameters
        self.max_actions_memory = 10000
        self.pattern_min_frequency = 3
        self.pattern_confidence_threshold = 0.7
        self.preference_confidence_threshold = 0.6
        
        # In-memory storage
        self.user_actions: List[UserAction] = []
        self.learned_patterns: Dict[str, UserPattern] = {}
        self.user_preferences: Dict[str, UserPreference] = {}
        self.context_embeddings: Dict[str, np.ndarray] = {}
        
        # Learning state
        self.learning_enabled = True
        self.last_analysis_time = 0
        self.analysis_interval = 3600  # 1 hour
        
        # Pattern detection
        self.temporal_patterns: Dict[str, List[Tuple[int, str]]] = defaultdict(list)  # hour -> actions
        self.sequential_patterns: List[List[str]] = []
        self.contextual_patterns: Dict[str, Counter] = defaultdict(Counter)
        
    async def start(self):
        """Start the learning service"""
        try:
            # Initialize database
            await self._initialize_database()
            
            # Load existing data
            await self._load_patterns()
            await self._load_preferences()
            await self._load_user_actions()
            
            # Start learning loop
            if self.learning_enabled:
                asyncio.create_task(self._learning_loop())
            
            self.logger.info("Learning Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start learning service: {e}")
            raise
    
    async def stop(self):
        """Stop the learning service"""
        # Save current state
        await self._save_patterns()
        await self._save_preferences()
        await self._save_user_actions()
        
        self.logger.info("Learning Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="learning_service",
                status=ServiceStatus.HEALTHY if self.learning_enabled else ServiceStatus.DEGRADED,
                details={
                    "learning_enabled": self.learning_enabled,
                    "actions_count": len(self.user_actions),
                    "patterns_count": len(self.learned_patterns),
                    "preferences_count": len(self.user_preferences),
                    "last_analysis": self.last_analysis_time,
                    "database_size": self._get_database_size()
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="learning_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def record_action(self, action_type: str, context: Dict[str, Any], 
                          success: bool = True, duration: float = 0.0, 
                          metadata: Dict[str, Any] = None):
        """Record a user action for learning"""
        if not self.learning_enabled:
            return
        
        try:
            action = UserAction(
                timestamp=time.time(),
                action_type=action_type,
                context=context,
                success=success,
                duration=duration,
                metadata=metadata or {}
            )
            
            self.user_actions.append(action)
            
            # Maintain memory limit
            if len(self.user_actions) > self.max_actions_memory:
                self.user_actions = self.user_actions[-self.max_actions_memory//2:]
            
            # Store in database
            await self._store_action_in_db(action)
            
            # Trigger real-time learning for certain actions
            if action_type in ['command', 'voice_input', 'file_access']:
                await self._update_real_time_patterns(action)
            
        except Exception as e:
            self.logger.error(f"Error recording action: {e}")
    
    async def get_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get personalized suggestions based on context"""
        try:
            suggestions = []
            
            # Get temporal suggestions
            temporal_suggestions = await self._get_temporal_suggestions(context)
            suggestions.extend(temporal_suggestions)
            
            # Get contextual suggestions
            contextual_suggestions = await self._get_contextual_suggestions(context)
            suggestions.extend(contextual_suggestions)
            
            # Get sequential suggestions
            sequential_suggestions = await self._get_sequential_suggestions(context)
            suggestions.extend(sequential_suggestions)
            
            # Sort by confidence and relevance
            suggestions.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Return top suggestions
            return suggestions[:5]
            
        except Exception as e:
            self.logger.error(f"Error getting suggestions: {e}")
            return []
    
    async def get_user_preferences(self) -> Dict[str, Any]:
        """Get learned user preferences"""
        return {
            key: {
                'value': pref.value,
                'confidence': pref.confidence,
                'last_updated': pref.last_updated
            }
            for key, pref in self.user_preferences.items()
            if pref.confidence >= self.preference_confidence_threshold
        }
    
    async def update_preference(self, key: str, value: Any, source: str = "manual"):
        """Update a user preference"""
        try:
            if key in self.user_preferences:
                pref = self.user_preferences[key]
                pref.value = value
                pref.learned_from.append(source)
                pref.last_updated = time.time()
                
                # Increase confidence for manual updates
                if source == "manual":
                    pref.confidence = min(1.0, pref.confidence + 0.2)
            else:
                self.user_preferences[key] = UserPreference(
                    key=key,
                    value=value,
                    confidence=0.8 if source == "manual" else 0.3,
                    learned_from=[source],
                    last_updated=time.time()
                )
            
            await self._save_preferences()
            
        except Exception as e:
            self.logger.error(f"Error updating preference: {e}")
    
    async def get_usage_patterns(self) -> Dict[str, Any]:
        """Get usage patterns analysis"""
        try:
            # Analyze temporal patterns
            hourly_usage = defaultdict(int)
            daily_usage = defaultdict(int)
            
            for action in self.user_actions:
                dt = datetime.fromtimestamp(action.timestamp)
                hourly_usage[dt.hour] += 1
                daily_usage[dt.weekday()] += 1
            
            # Most used features
            feature_usage = Counter(action.action_type for action in self.user_actions)
            
            # Success rates
            success_rates = {}
            for action_type in feature_usage.keys():
                actions_of_type = [a for a in self.user_actions if a.action_type == action_type]
                successful = sum(1 for a in actions_of_type if a.success)
                success_rates[action_type] = successful / len(actions_of_type) if actions_of_type else 0
            
            return {
                "hourly_usage": dict(hourly_usage),
                "daily_usage": dict(daily_usage),
                "feature_usage": dict(feature_usage.most_common(10)),
                "success_rates": success_rates,
                "total_actions": len(self.user_actions),
                "patterns_learned": len(self.learned_patterns)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing usage patterns: {e}")
            return {}
    
    async def _learning_loop(self):
        """Main learning analysis loop"""
        while self.learning_enabled:
            try:
                await asyncio.sleep(self.analysis_interval)
                
                # Run pattern analysis
                await self._analyze_patterns()
                
                # Update preferences
                await self._update_preferences()
                
                # Clean old data
                await self._cleanup_old_data()
                
                self.last_analysis_time = time.time()
                
            except Exception as e:
                self.logger.error(f"Error in learning loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _analyze_patterns(self):
        """Analyze user actions to discover patterns"""
        try:
            # Temporal pattern analysis
            await self._analyze_temporal_patterns()
            
            # Sequential pattern analysis
            await self._analyze_sequential_patterns()
            
            # Contextual pattern analysis
            await self._analyze_contextual_patterns()
            
            # Save discovered patterns
            await self._save_patterns()
            
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")
    
    async def _analyze_temporal_patterns(self):
        """Analyze temporal usage patterns"""
        try:
            # Group actions by hour of day
            hourly_actions = defaultdict(list)
            
            for action in self.user_actions:
                dt = datetime.fromtimestamp(action.timestamp)
                hour = dt.hour
                hourly_actions[hour].append(action)
            
            # Find patterns for each hour
            for hour, actions in hourly_actions.items():
                if len(actions) >= self.pattern_min_frequency:
                    # Analyze common action types in this hour
                    action_types = Counter(a.action_type for a in actions)
                    most_common = action_types.most_common(3)
                    
                    if most_common and most_common[0][1] >= self.pattern_min_frequency:
                        pattern_id = f"temporal_hour_{hour}"
                        
                        pattern = UserPattern(
                            pattern_id=pattern_id,
                            pattern_type="temporal",
                            confidence=min(1.0, most_common[0][1] / len(actions)),
                            frequency=most_common[0][1],
                            last_seen=max(a.timestamp for a in actions),
                            description=f"User typically performs {most_common[0][0]} around {hour}:00",
                            triggers=[f"time_hour_{hour}"],
                            suggestions=[f"Ready to help with {most_common[0][0]}?"]
                        )
                        
                        if pattern.confidence >= self.pattern_confidence_threshold:
                            self.learned_patterns[pattern_id] = pattern
            
        except Exception as e:
            self.logger.error(f"Error analyzing temporal patterns: {e}")
    
    async def _analyze_sequential_patterns(self):
        """Analyze sequential action patterns"""
        try:
            # Create sequences of actions
            sequences = []
            current_sequence = []
            
            for action in sorted(self.user_actions, key=lambda x: x.timestamp):
                # Start new sequence if gap is too large (> 10 minutes)
                if (current_sequence and 
                    action.timestamp - current_sequence[-1].timestamp > 600):
                    if len(current_sequence) >= 2:
                        sequences.append([a.action_type for a in current_sequence])
                    current_sequence = []
                
                current_sequence.append(action)
            
            # Add final sequence
            if len(current_sequence) >= 2:
                sequences.append([a.action_type for a in current_sequence])
            
            # Find common subsequences
            subsequence_counts = Counter()
            
            for sequence in sequences:
                for i in range(len(sequence) - 1):
                    for j in range(i + 2, min(i + 5, len(sequence) + 1)):  # Max length 4
                        subseq = tuple(sequence[i:j])
                        subsequence_counts[subseq] += 1
            
            # Create patterns from frequent subsequences
            for subseq, count in subsequence_counts.items():
                if count >= self.pattern_min_frequency:
                    pattern_id = f"sequential_{'_'.join(subseq)}"
                    
                    pattern = UserPattern(
                        pattern_id=pattern_id,
                        pattern_type="sequential",
                        confidence=min(1.0, count / len(sequences)),
                        frequency=count,
                        last_seen=time.time(),
                        description=f"User often follows {' -> '.join(subseq)}",
                        triggers=list(subseq[:-1]),
                        suggestions=[f"Next: {subseq[-1]}?"]
                    )
                    
                    if pattern.confidence >= self.pattern_confidence_threshold:
                        self.learned_patterns[pattern_id] = pattern
            
        except Exception as e:
            self.logger.error(f"Error analyzing sequential patterns: {e}")
    
    async def _analyze_contextual_patterns(self):
        """Analyze contextual patterns"""
        try:
            # Group actions by context similarity
            context_groups = defaultdict(list)
            
            for action in self.user_actions:
                # Create context signature
                context_sig = self._create_context_signature(action.context)
                context_groups[context_sig].append(action)
            
            # Find patterns in each context group
            for context_sig, actions in context_groups.items():
                if len(actions) >= self.pattern_min_frequency:
                    action_types = Counter(a.action_type for a in actions)
                    most_common = action_types.most_common(1)
                    
                    if most_common and most_common[0][1] >= self.pattern_min_frequency:
                        pattern_id = f"contextual_{hashlib.md5(context_sig.encode()).hexdigest()[:8]}"
                        
                        pattern = UserPattern(
                            pattern_id=pattern_id,
                            pattern_type="contextual",
                            confidence=min(1.0, most_common[0][1] / len(actions)),
                            frequency=most_common[0][1],
                            last_seen=max(a.timestamp for a in actions),
                            description=f"In context '{context_sig}', user typically does {most_common[0][0]}",
                            triggers=[context_sig],
                            suggestions=[f"Would you like to {most_common[0][0]}?"]
                        )
                        
                        if pattern.confidence >= self.pattern_confidence_threshold:
                            self.learned_patterns[pattern_id] = pattern
            
        except Exception as e:
            self.logger.error(f"Error analyzing contextual patterns: {e}")
    
    def _create_context_signature(self, context: Dict[str, Any]) -> str:
        """Create a signature for context matching"""
        # Extract key context elements
        key_elements = []
        
        for key in ['app', 'file_type', 'time_of_day', 'day_of_week']:
            if key in context:
                key_elements.append(f"{key}:{context[key]}")
        
        return "|".join(sorted(key_elements))
    
    async def _update_real_time_patterns(self, action: UserAction):
        """Update patterns in real-time for immediate learning"""
        try:
            # Update temporal patterns
            dt = datetime.fromtimestamp(action.timestamp)
            hour_key = f"hour_{dt.hour}"
            
            if hour_key not in self.temporal_patterns:
                self.temporal_patterns[hour_key] = []
            
            self.temporal_patterns[hour_key].append((int(action.timestamp), action.action_type))
            
            # Keep only recent entries (last 30 days)
            cutoff_time = time.time() - (30 * 24 * 3600)
            self.temporal_patterns[hour_key] = [
                (ts, at) for ts, at in self.temporal_patterns[hour_key] 
                if ts > cutoff_time
            ]
            
        except Exception as e:
            self.logger.error(f"Error updating real-time patterns: {e}")
    
    async def _update_preferences(self):
        """Update user preferences based on actions"""
        try:
            # Analyze preferred file types
            file_types = [
                action.context.get('file_type') 
                for action in self.user_actions 
                if action.context.get('file_type') and action.success
            ]
            
            if file_types:
                file_type_counts = Counter(file_types)
                most_common_type = file_type_counts.most_common(1)[0]
                
                if most_common_type[1] >= 5:  # At least 5 occurrences
                    await self.update_preference(
                        'preferred_file_type', 
                        most_common_type[0], 
                        'learned_from_usage'
                    )
            
            # Analyze preferred working hours
            work_hours = [
                datetime.fromtimestamp(action.timestamp).hour
                for action in self.user_actions
                if action.action_type in ['command', 'file_access']
            ]
            
            if work_hours:
                hour_counts = Counter(work_hours)
                peak_hours = [hour for hour, count in hour_counts.items() if count >= 5]
                
                if peak_hours:
                    await self.update_preference(
                        'active_hours',
                        peak_hours,
                        'learned_from_usage'
                    )
            
            # Analyze command preferences
            commands = [
                action.context.get('command')
                for action in self.user_actions
                if action.action_type == 'command' and action.context.get('command') and action.success
            ]
            
            if commands:
                command_counts = Counter(commands)
                favorite_commands = [cmd for cmd, count in command_counts.items() if count >= 3]
                
                if favorite_commands:
                    await self.update_preference(
                        'favorite_commands',
                        favorite_commands[:10],  # Top 10
                        'learned_from_usage'
                    )
            
        except Exception as e:
            self.logger.error(f"Error updating preferences: {e}")
    
    async def _get_temporal_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get suggestions based on temporal patterns"""
        suggestions = []
        
        try:
            current_hour = datetime.now().hour
            hour_pattern_id = f"temporal_hour_{current_hour}"
            
            if hour_pattern_id in self.learned_patterns:
                pattern = self.learned_patterns[hour_pattern_id]
                
                suggestions.append({
                    'type': 'temporal',
                    'title': 'Based on your usual schedule',
                    'description': pattern.description,
                    'suggestions': pattern.suggestions,
                    'confidence': pattern.confidence
                })
        
        except Exception as e:
            self.logger.error(f"Error getting temporal suggestions: {e}")
        
        return suggestions
    
    async def _get_contextual_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get suggestions based on contextual patterns"""
        suggestions = []
        
        try:
            context_sig = self._create_context_signature(context)
            
            for pattern in self.learned_patterns.values():
                if (pattern.pattern_type == "contextual" and 
                    context_sig in pattern.triggers):
                    
                    suggestions.append({
                        'type': 'contextual',
                        'title': 'Based on current context',
                        'description': pattern.description,
                        'suggestions': pattern.suggestions,
                        'confidence': pattern.confidence
                    })
        
        except Exception as e:
            self.logger.error(f"Error getting contextual suggestions: {e}")
        
        return suggestions
    
    async def _get_sequential_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get suggestions based on sequential patterns"""
        suggestions = []
        
        try:
            # Get recent actions
            recent_actions = [
                action.action_type for action in self.user_actions[-5:]
                if time.time() - action.timestamp < 3600  # Last hour
            ]
            
            if recent_actions:
                for pattern in self.learned_patterns.values():
                    if pattern.pattern_type == "sequential":
                        # Check if recent actions match pattern triggers
                        if all(trigger in recent_actions for trigger in pattern.triggers):
                            suggestions.append({
                                'type': 'sequential',
                                'title': 'Continue your workflow',
                                'description': pattern.description,
                                'suggestions': pattern.suggestions,
                                'confidence': pattern.confidence
                            })
        
        except Exception as e:
            self.logger.error(f"Error getting sequential suggestions: {e}")
        
        return suggestions
    
    async def _initialize_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    action_type TEXT,
                    context TEXT,
                    success BOOLEAN,
                    duration REAL,
                    metadata TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON user_actions(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_action_type ON user_actions(action_type)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    async def _store_action_in_db(self, action: UserAction):
        """Store action in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_actions 
                (timestamp, action_type, context, success, duration, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                action.timestamp,
                action.action_type,
                json.dumps(action.context),
                action.success,
                action.duration,
                json.dumps(action.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing action in database: {e}")
    
    async def _load_user_actions(self):
        """Load recent user actions from database"""
        try:
            if not self.db_path.exists():
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load recent actions (last 30 days)
            cutoff_time = time.time() - (30 * 24 * 3600)
            
            cursor.execute('''
                SELECT timestamp, action_type, context, success, duration, metadata
                FROM user_actions
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (cutoff_time, self.max_actions_memory))
            
            rows = cursor.fetchall()
            
            for row in rows:
                action = UserAction(
                    timestamp=row[0],
                    action_type=row[1],
                    context=json.loads(row[2]),
                    success=bool(row[3]),
                    duration=row[4],
                    metadata=json.loads(row[5]) if row[5] else {}
                )
                self.user_actions.append(action)
            
            conn.close()
            
            self.logger.info(f"Loaded {len(self.user_actions)} user actions from database")
            
        except Exception as e:
            self.logger.error(f"Error loading user actions: {e}")
    
    async def _save_patterns(self):
        """Save learned patterns to file"""
        try:
            patterns_data = {
                pattern_id: asdict(pattern)
                for pattern_id, pattern in self.learned_patterns.items()
            }
            
            with open(self.patterns_file, 'w') as f:
                json.dump(patterns_data, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error saving patterns: {e}")
    
    async def _load_patterns(self):
        """Load learned patterns from file"""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, 'r') as f:
                    patterns_data = json.load(f)
                
                for pattern_id, pattern_dict in patterns_data.items():
                    pattern = UserPattern(**pattern_dict)
                    self.learned_patterns[pattern_id] = pattern
                
                self.logger.info(f"Loaded {len(self.learned_patterns)} patterns")
            
        except Exception as e:
            self.logger.error(f"Error loading patterns: {e}")
    
    async def _save_preferences(self):
        """Save user preferences to file"""
        try:
            preferences_data = {
                key: asdict(pref)
                for key, pref in self.user_preferences.items()
            }
            
            with open(self.preferences_file, 'w') as f:
                json.dump(preferences_data, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error saving preferences: {e}")
    
    async def _load_preferences(self):
        """Load user preferences from file"""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, 'r') as f:
                    preferences_data = json.load(f)
                
                for key, pref_dict in preferences_data.items():
                    pref = UserPreference(**pref_dict)
                    self.user_preferences[key] = pref
                
                self.logger.info(f"Loaded {len(self.user_preferences)} preferences")
            
        except Exception as e:
            self.logger.error(f"Error loading preferences: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data to maintain performance"""
        try:
            # Remove old actions from memory
            cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days
            self.user_actions = [
                action for action in self.user_actions
                if action.timestamp > cutoff_time
            ]
            
            # Remove old patterns with low confidence
            patterns_to_remove = [
                pattern_id for pattern_id, pattern in self.learned_patterns.items()
                if (time.time() - pattern.last_seen > 7 * 24 * 3600 and  # 7 days old
                    pattern.confidence < 0.5)
            ]
            
            for pattern_id in patterns_to_remove:
                del self.learned_patterns[pattern_id]
            
            # Clean database
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM user_actions 
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                conn.commit()
                conn.close()
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    def _get_database_size(self) -> int:
        """Get database file size in bytes"""
        try:
            if self.db_path.exists():
                return self.db_path.stat().st_size
            return 0
        except:
            return 0
    
    def set_learning_enabled(self, enabled: bool):
        """Enable or disable learning"""
        self.learning_enabled = enabled
        self.logger.info(f"Learning {'enabled' if enabled else 'disabled'}")
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning service statistics"""
        return {
            "learning_enabled": self.learning_enabled,
            "actions_recorded": len(self.user_actions),
            "patterns_learned": len(self.learned_patterns),
            "preferences_learned": len(self.user_preferences),
            "database_size_mb": self._get_database_size() / (1024 * 1024),
            "last_analysis": self.last_analysis_time,
            "pattern_types": {
                ptype: len([p for p in self.learned_patterns.values() if p.pattern_type == ptype])
                for ptype in ['temporal', 'sequential', 'contextual']
            }
        }