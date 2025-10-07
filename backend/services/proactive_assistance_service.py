"""
Proactive Assistance Service for AI Assistant
Monitors user activity and provides intelligent suggestions
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class SuggestionType(Enum):
    """Types of proactive suggestions"""
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    TASK_AUTOMATION = "task_automation"
    PRODUCTIVITY_TIP = "productivity_tip"
    SYSTEM_MAINTENANCE = "system_maintenance"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    TIME_MANAGEMENT = "time_management"

class SuggestionPriority(Enum):
    """Priority levels for suggestions"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class ActivityPattern:
    """Represents a detected user activity pattern"""
    pattern_id: str
    pattern_type: str
    frequency: float
    last_occurrence: float
    confidence: float
    metadata: Dict[str, Any]

@dataclass
class ProactiveSuggestion:
    """Represents a proactive suggestion"""
    suggestion_id: str
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    action_text: str
    action_data: Dict[str, Any]
    created_at: float
    expires_at: Optional[float]
    shown_count: int
    dismissed: bool
    accepted: bool

class ProactiveAssistanceService:
    """Service for proactive assistance and monitoring"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Activity monitoring
        self.activity_log: List[Dict[str, Any]] = []
        self.activity_patterns: Dict[str, ActivityPattern] = {}
        self.user_preferences: Dict[str, Any] = {}
        
        # Suggestions
        self.active_suggestions: Dict[str, ProactiveSuggestion] = {}
        self.suggestion_history: List[Dict[str, Any]] = []
        
        # Monitoring settings
        self.monitoring_enabled = True
        self.suggestion_cooldown = 300  # 5 minutes between suggestions
        self.last_suggestion_time = 0
        
        # Pattern detection
        self.pattern_detection_interval = 3600  # 1 hour
        self.last_pattern_analysis = 0
        
        # Context awareness
        self.current_context: Dict[str, Any] = {}
        self.context_history: List[Dict[str, Any]] = []
        
    async def start(self):
        """Start the proactive assistance service"""
        try:
            # Load user preferences and patterns
            await self._load_user_data()
            
            # Start monitoring loops
            asyncio.create_task(self._activity_monitoring_loop())
            asyncio.create_task(self._pattern_analysis_loop())
            asyncio.create_task(self._suggestion_generation_loop())
            asyncio.create_task(self._context_monitoring_loop())
            
            self.logger.info("Proactive Assistance Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start proactive assistance service: {e}")
            raise
    
    async def stop(self):
        """Stop the proactive assistance service"""
        # Save user data
        await self._save_user_data()
        
        self.logger.info("Proactive Assistance Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="proactive_assistance_service",
                status=ServiceStatus.HEALTHY,
                details={
                    "monitoring_enabled": self.monitoring_enabled,
                    "activity_log_size": len(self.activity_log),
                    "detected_patterns": len(self.activity_patterns),
                    "active_suggestions": len(self.active_suggestions),
                    "suggestion_history": len(self.suggestion_history)
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="proactive_assistance_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def log_activity(self, activity_type: str, details: Dict[str, Any]):
        """Log user activity for pattern detection"""
        try:
            if not self.monitoring_enabled:
                return
            
            activity_entry = {
                "timestamp": time.time(),
                "activity_type": activity_type,
                "details": details,
                "context": self.current_context.copy()
            }
            
            self.activity_log.append(activity_entry)
            
            # Keep log manageable
            if len(self.activity_log) > 1000:
                self.activity_log = self.activity_log[-500:]
            
            # Update current context
            await self._update_context(activity_type, details)
            
        except Exception as e:
            self.logger.error(f"Error logging activity: {e}")
    
    async def get_suggestions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get current proactive suggestions"""
        try:
            # Filter active, non-dismissed suggestions
            active_suggestions = [
                suggestion for suggestion in self.active_suggestions.values()
                if not suggestion.dismissed and (
                    not suggestion.expires_at or 
                    suggestion.expires_at > time.time()
                )
            ]
            
            # Sort by priority and creation time
            active_suggestions.sort(
                key=lambda s: (s.priority.value, -s.created_at),
                reverse=True
            )
            
            return [asdict(suggestion) for suggestion in active_suggestions[:limit]]
            
        except Exception as e:
            self.logger.error(f"Error getting suggestions: {e}")
            return []
    
    async def dismiss_suggestion(self, suggestion_id: str) -> bool:
        """Dismiss a suggestion"""
        try:
            if suggestion_id in self.active_suggestions:
                suggestion = self.active_suggestions[suggestion_id]
                suggestion.dismissed = True
                
                # Log dismissal
                self.suggestion_history.append({
                    "suggestion_id": suggestion_id,
                    "action": "dismissed",
                    "timestamp": time.time()
                })
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error dismissing suggestion: {e}")
            return False
    
    async def accept_suggestion(self, suggestion_id: str) -> Dict[str, Any]:
        """Accept and execute a suggestion"""
        try:
            if suggestion_id not in self.active_suggestions:
                return {"success": False, "error": "Suggestion not found"}
            
            suggestion = self.active_suggestions[suggestion_id]
            suggestion.accepted = True
            
            # Log acceptance
            self.suggestion_history.append({
                "suggestion_id": suggestion_id,
                "action": "accepted",
                "timestamp": time.time()
            })
            
            # Execute suggestion action
            result = await self._execute_suggestion_action(suggestion)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            self.logger.error(f"Error accepting suggestion: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences for proactive assistance"""
        try:
            self.user_preferences.update(preferences)
            await self._save_user_data()
            
        except Exception as e:
            self.logger.error(f"Error updating preferences: {e}")
    
    async def _activity_monitoring_loop(self):
        """Monitor system and user activity"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Monitor system resources
                await self._monitor_system_resources()
                
                # Monitor application usage
                await self._monitor_application_usage()
                
                # Monitor file system activity
                await self._monitor_file_activity()
                
            except Exception as e:
                self.logger.error(f"Error in activity monitoring: {e}")
    
    async def _pattern_analysis_loop(self):
        """Analyze activity patterns"""
        while True:
            try:
                await asyncio.sleep(self.pattern_detection_interval)
                
                current_time = time.time()
                if current_time - self.last_pattern_analysis < self.pattern_detection_interval:
                    continue
                
                await self._analyze_activity_patterns()
                self.last_pattern_analysis = current_time
                
            except Exception as e:
                self.logger.error(f"Error in pattern analysis: {e}")
    
    async def _suggestion_generation_loop(self):
        """Generate proactive suggestions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = time.time()
                if current_time - self.last_suggestion_time < self.suggestion_cooldown:
                    continue
                
                # Generate suggestions based on patterns and context
                await self._generate_suggestions()
                
            except Exception as e:
                self.logger.error(f"Error in suggestion generation: {e}")
    
    async def _context_monitoring_loop(self):
        """Monitor and update current context"""
        while True:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                # Update time-based context
                await self._update_time_context()
                
                # Update work session context
                await self._update_work_session_context()
                
                # Clean old context history
                await self._clean_context_history()
                
            except Exception as e:
                self.logger.error(f"Error in context monitoring: {e}")
    
    async def _monitor_system_resources(self):
        """Monitor system resource usage"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                await self.log_activity("high_cpu_usage", {"cpu_percent": cpu_percent})
            
            # Memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                await self.log_activity("high_memory_usage", {"memory_percent": memory.percent})
            
            # Disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                await self.log_activity("low_disk_space", {"disk_percent": disk.percent})
            
        except Exception as e:
            self.logger.error(f"Error monitoring system resources: {e}")
    
    async def _monitor_application_usage(self):
        """Monitor application usage patterns"""
        try:
            # This would integrate with system APIs to track app usage
            # For now, we'll simulate some activity
            pass
            
        except Exception as e:
            self.logger.error(f"Error monitoring application usage: {e}")
    
    async def _monitor_file_activity(self):
        """Monitor file system activity"""
        try:
            # This would monitor file creation, modification, deletion
            # For now, we'll simulate some activity
            pass
            
        except Exception as e:
            self.logger.error(f"Error monitoring file activity: {e}")
    
    async def _analyze_activity_patterns(self):
        """Analyze user activity patterns"""
        try:
            current_time = time.time()
            
            # Analyze recent activity (last 24 hours)
            recent_activities = [
                activity for activity in self.activity_log
                if current_time - activity["timestamp"] < 86400
            ]
            
            # Group activities by type
            activity_groups = {}
            for activity in recent_activities:
                activity_type = activity["activity_type"]
                if activity_type not in activity_groups:
                    activity_groups[activity_type] = []
                activity_groups[activity_type].append(activity)
            
            # Detect patterns
            for activity_type, activities in activity_groups.items():
                if len(activities) >= 3:  # Need at least 3 occurrences
                    pattern = await self._detect_pattern(activity_type, activities)
                    if pattern:
                        self.activity_patterns[pattern.pattern_id] = pattern
            
        except Exception as e:
            self.logger.error(f"Error analyzing activity patterns: {e}")
    
    async def _detect_pattern(self, activity_type: str, activities: List[Dict[str, Any]]) -> Optional[ActivityPattern]:
        """Detect a specific activity pattern"""
        try:
            if len(activities) < 3:
                return None
            
            # Calculate frequency (activities per hour)
            time_span = activities[-1]["timestamp"] - activities[0]["timestamp"]
            frequency = len(activities) / (time_span / 3600) if time_span > 0 else 0
            
            # Calculate confidence based on regularity
            intervals = []
            for i in range(1, len(activities)):
                interval = activities[i]["timestamp"] - activities[i-1]["timestamp"]
                intervals.append(interval)
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                confidence = max(0, 1 - (variance / (avg_interval ** 2))) if avg_interval > 0 else 0
            else:
                confidence = 0
            
            pattern_id = f"{activity_type}_{int(time.time())}"
            
            return ActivityPattern(
                pattern_id=pattern_id,
                pattern_type=activity_type,
                frequency=frequency,
                last_occurrence=activities[-1]["timestamp"],
                confidence=confidence,
                metadata={
                    "activity_count": len(activities),
                    "time_span": time_span,
                    "average_interval": avg_interval if intervals else 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting pattern: {e}")
            return None
    
    async def _generate_suggestions(self):
        """Generate proactive suggestions"""
        try:
            suggestions = []
            
            # Generate suggestions based on patterns
            for pattern in self.activity_patterns.values():
                suggestion = await self._generate_pattern_suggestion(pattern)
                if suggestion:
                    suggestions.append(suggestion)
            
            # Generate suggestions based on context
            context_suggestions = await self._generate_context_suggestions()
            suggestions.extend(context_suggestions)
            
            # Generate time-based suggestions
            time_suggestions = await self._generate_time_based_suggestions()
            suggestions.extend(time_suggestions)
            
            # Add suggestions to active list
            for suggestion in suggestions:
                if suggestion.suggestion_id not in self.active_suggestions:
                    self.active_suggestions[suggestion.suggestion_id] = suggestion
                    self.last_suggestion_time = time.time()
            
            # Clean expired suggestions
            await self._clean_expired_suggestions()
            
        except Exception as e:
            self.logger.error(f"Error generating suggestions: {e}")
    
    async def _generate_pattern_suggestion(self, pattern: ActivityPattern) -> Optional[ProactiveSuggestion]:
        """Generate suggestion based on activity pattern"""
        try:
            current_time = time.time()
            
            # Don't suggest if pattern was recent
            if current_time - pattern.last_occurrence < 3600:  # 1 hour
                return None
            
            # Generate suggestion based on pattern type
            if pattern.pattern_type == "file_creation" and pattern.frequency > 2:
                return ProactiveSuggestion(
                    suggestion_id=f"automation_{pattern.pattern_id}",
                    suggestion_type=SuggestionType.TASK_AUTOMATION,
                    priority=SuggestionPriority.MEDIUM,
                    title="Automate File Creation",
                    description=f"I noticed you create files frequently. Would you like me to create a template or automation?",
                    action_text="Create Automation",
                    action_data={"pattern_id": pattern.pattern_id, "action": "create_file_automation"},
                    created_at=current_time,
                    expires_at=current_time + 86400,  # 24 hours
                    shown_count=0,
                    dismissed=False,
                    accepted=False
                )
            
            elif pattern.pattern_type == "high_cpu_usage" and pattern.frequency > 1:
                return ProactiveSuggestion(
                    suggestion_id=f"performance_{pattern.pattern_id}",
                    suggestion_type=SuggestionType.SYSTEM_MAINTENANCE,
                    priority=SuggestionPriority.HIGH,
                    title="System Performance Issue",
                    description="I've noticed high CPU usage patterns. Would you like me to analyze and optimize your system?",
                    action_text="Optimize System",
                    action_data={"pattern_id": pattern.pattern_id, "action": "system_optimization"},
                    created_at=current_time,
                    expires_at=current_time + 43200,  # 12 hours
                    shown_count=0,
                    dismissed=False,
                    accepted=False
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating pattern suggestion: {e}")
            return None
    
    async def _generate_context_suggestions(self) -> List[ProactiveSuggestion]:
        """Generate suggestions based on current context"""
        suggestions = []
        current_time = time.time()
        
        try:
            # Work session suggestions
            if self.current_context.get("work_session_active"):
                session_duration = current_time - self.current_context.get("work_session_start", current_time)
                
                if session_duration > 7200:  # 2 hours
                    suggestions.append(ProactiveSuggestion(
                        suggestion_id=f"break_reminder_{int(current_time)}",
                        suggestion_type=SuggestionType.TIME_MANAGEMENT,
                        priority=SuggestionPriority.MEDIUM,
                        title="Take a Break",
                        description="You've been working for over 2 hours. Consider taking a short break to maintain productivity.",
                        action_text="Schedule Break",
                        action_data={"action": "schedule_break", "duration": 15},
                        created_at=current_time,
                        expires_at=current_time + 3600,  # 1 hour
                        shown_count=0,
                        dismissed=False,
                        accepted=False
                    ))
            
            # Learning opportunities
            if self.current_context.get("repeated_manual_task"):
                suggestions.append(ProactiveSuggestion(
                    suggestion_id=f"learning_{int(current_time)}",
                    suggestion_type=SuggestionType.LEARNING_OPPORTUNITY,
                    priority=SuggestionPriority.LOW,
                    title="Learn Automation",
                    description="I can teach you how to automate this repetitive task. Would you like a quick tutorial?",
                    action_text="Start Tutorial",
                    action_data={"action": "automation_tutorial", "task_type": "general"},
                    created_at=current_time,
                    expires_at=current_time + 86400,  # 24 hours
                    shown_count=0,
                    dismissed=False,
                    accepted=False
                ))
            
        except Exception as e:
            self.logger.error(f"Error generating context suggestions: {e}")
        
        return suggestions
    
    async def _generate_time_based_suggestions(self) -> List[ProactiveSuggestion]:
        """Generate suggestions based on time of day"""
        suggestions = []
        current_time = time.time()
        current_hour = datetime.now().hour
        
        try:
            # Morning productivity suggestions
            if 8 <= current_hour <= 10:
                suggestions.append(ProactiveSuggestion(
                    suggestion_id=f"morning_planning_{int(current_time)}",
                    suggestion_type=SuggestionType.PRODUCTIVITY_TIP,
                    priority=SuggestionPriority.LOW,
                    title="Plan Your Day",
                    description="Good morning! Would you like me to help you plan your tasks for today?",
                    action_text="Plan Day",
                    action_data={"action": "daily_planning"},
                    created_at=current_time,
                    expires_at=current_time + 7200,  # 2 hours
                    shown_count=0,
                    dismissed=False,
                    accepted=False
                ))
            
            # End of day suggestions
            elif 17 <= current_hour <= 19:
                suggestions.append(ProactiveSuggestion(
                    suggestion_id=f"day_review_{int(current_time)}",
                    suggestion_type=SuggestionType.PRODUCTIVITY_TIP,
                    priority=SuggestionPriority.LOW,
                    title="Review Your Day",
                    description="Would you like me to help you review what you accomplished today?",
                    action_text="Review Day",
                    action_data={"action": "daily_review"},
                    created_at=current_time,
                    expires_at=current_time + 7200,  # 2 hours
                    shown_count=0,
                    dismissed=False,
                    accepted=False
                ))
            
        except Exception as e:
            self.logger.error(f"Error generating time-based suggestions: {e}")
        
        return suggestions
    
    async def _execute_suggestion_action(self, suggestion: ProactiveSuggestion) -> Dict[str, Any]:
        """Execute the action associated with a suggestion"""
        try:
            action = suggestion.action_data.get("action")
            
            if action == "create_file_automation":
                return await self._create_file_automation(suggestion.action_data)
            elif action == "system_optimization":
                return await self._perform_system_optimization(suggestion.action_data)
            elif action == "schedule_break":
                return await self._schedule_break(suggestion.action_data)
            elif action == "automation_tutorial":
                return await self._start_automation_tutorial(suggestion.action_data)
            elif action == "daily_planning":
                return await self._start_daily_planning()
            elif action == "daily_review":
                return await self._start_daily_review()
            else:
                return {"status": "unknown_action", "action": action}
            
        except Exception as e:
            self.logger.error(f"Error executing suggestion action: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _create_file_automation(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create file automation based on detected pattern"""
        # This would integrate with the automation service
        return {"status": "automation_created", "type": "file_creation"}
    
    async def _perform_system_optimization(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform system optimization"""
        # This would integrate with system optimization tools
        return {"status": "optimization_started", "estimated_time": 300}
    
    async def _schedule_break(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a break reminder"""
        duration = action_data.get("duration", 15)
        return {"status": "break_scheduled", "duration_minutes": duration}
    
    async def _start_automation_tutorial(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start automation tutorial"""
        # This would integrate with the demo service
        return {"status": "tutorial_started", "type": "automation"}
    
    async def _start_daily_planning(self) -> Dict[str, Any]:
        """Start daily planning session"""
        return {"status": "planning_started", "mode": "daily"}
    
    async def _start_daily_review(self) -> Dict[str, Any]:
        """Start daily review session"""
        return {"status": "review_started", "mode": "daily"}
    
    async def _update_context(self, activity_type: str, details: Dict[str, Any]):
        """Update current context based on activity"""
        try:
            current_time = time.time()
            
            # Update work session context
            if activity_type in ["file_creation", "application_usage", "typing_activity"]:
                if not self.current_context.get("work_session_active"):
                    self.current_context["work_session_active"] = True
                    self.current_context["work_session_start"] = current_time
                
                self.current_context["last_activity"] = current_time
            
            # Detect repeated manual tasks
            if activity_type == "manual_task":
                manual_tasks = self.current_context.get("manual_task_count", 0) + 1
                self.current_context["manual_task_count"] = manual_tasks
                
                if manual_tasks >= 3:
                    self.current_context["repeated_manual_task"] = True
            
            # Store context history
            self.context_history.append({
                "timestamp": current_time,
                "context": self.current_context.copy()
            })
            
        except Exception as e:
            self.logger.error(f"Error updating context: {e}")
    
    async def _update_time_context(self):
        """Update time-based context"""
        try:
            current_time = time.time()
            current_hour = datetime.now().hour
            
            self.current_context["current_hour"] = current_hour
            self.current_context["is_work_hours"] = 9 <= current_hour <= 17
            
            # Check for work session timeout
            if self.current_context.get("work_session_active"):
                last_activity = self.current_context.get("last_activity", current_time)
                if current_time - last_activity > 1800:  # 30 minutes of inactivity
                    self.current_context["work_session_active"] = False
                    self.current_context.pop("work_session_start", None)
            
        except Exception as e:
            self.logger.error(f"Error updating time context: {e}")
    
    async def _update_work_session_context(self):
        """Update work session context"""
        try:
            # This would analyze current applications, files, etc.
            pass
            
        except Exception as e:
            self.logger.error(f"Error updating work session context: {e}")
    
    async def _clean_context_history(self):
        """Clean old context history"""
        try:
            current_time = time.time()
            
            # Keep only last 24 hours of context history
            self.context_history = [
                entry for entry in self.context_history
                if current_time - entry["timestamp"] < 86400
            ]
            
        except Exception as e:
            self.logger.error(f"Error cleaning context history: {e}")
    
    async def _clean_expired_suggestions(self):
        """Clean expired suggestions"""
        try:
            current_time = time.time()
            
            expired_suggestions = [
                suggestion_id for suggestion_id, suggestion in self.active_suggestions.items()
                if suggestion.expires_at and suggestion.expires_at < current_time
            ]
            
            for suggestion_id in expired_suggestions:
                del self.active_suggestions[suggestion_id]
            
        except Exception as e:
            self.logger.error(f"Error cleaning expired suggestions: {e}")
    
    async def _load_user_data(self):
        """Load user preferences and patterns"""
        try:
            data_file = self.config.get_data_path("proactive_assistance.json")
            
            if data_file.exists():
                with open(data_file, 'r') as f:
                    data = json.load(f)
                
                self.user_preferences = data.get("preferences", {})
                
                # Load patterns
                patterns_data = data.get("patterns", {})
                for pattern_id, pattern_data in patterns_data.items():
                    self.activity_patterns[pattern_id] = ActivityPattern(**pattern_data)
            
        except Exception as e:
            self.logger.error(f"Error loading user data: {e}")
    
    async def _save_user_data(self):
        """Save user preferences and patterns"""
        try:
            data = {
                "preferences": self.user_preferences,
                "patterns": {
                    pattern_id: asdict(pattern)
                    for pattern_id, pattern in self.activity_patterns.items()
                },
                "last_saved": time.time()
            }
            
            data_file = self.config.get_data_path("proactive_assistance.json")
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error saving user data: {e}")
    
    def get_assistance_stats(self) -> Dict[str, Any]:
        """Get proactive assistance statistics"""
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "activity_log_size": len(self.activity_log),
            "detected_patterns": len(self.activity_patterns),
            "active_suggestions": len(self.active_suggestions),
            "suggestion_history": len(self.suggestion_history),
            "last_suggestion_time": self.last_suggestion_time,
            "current_context_keys": list(self.current_context.keys())
        }