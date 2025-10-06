"""
Auto-Update Service for AI Assistant
Handles automatic updates, rollbacks, and version management
"""

import asyncio
import logging
import json
import hashlib
import zipfile
import shutil
import subprocess
import sys
import os
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import aiohttp
import aiofiles
from packaging import version

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

class UpdateInfo:
    """Information about an available update"""
    def __init__(self, version: str, download_url: str, changelog: str, 
                 size: int, checksum: str, critical: bool = False):
        self.version = version
        self.download_url = download_url
        self.changelog = changelog
        self.size = size
        self.checksum = checksum
        self.critical = critical
        self.release_date = datetime.now()

class UpdaterService:
    """Service for handling automatic updates"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.current_version = self._get_current_version()
        self.update_server_url = config.get('update_server_url', 'https://api.github.com/repos/ai-assistant/releases')
        self.check_interval = config.get('update_check_interval', 3600)  # 1 hour
        self.auto_update_enabled = config.get('auto_update_enabled', True)
        self.auto_install_enabled = config.get('auto_install_enabled', False)
        
        # Paths
        self.updates_dir = config.get_data_path("updates")
        self.backup_dir = config.get_data_path("backups")
        self.temp_dir = config.get_temp_path()
        
        # Create directories
        self.updates_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Update state
        self.is_checking = False
        self.is_updating = False
        self.available_update: Optional[UpdateInfo] = None
        self.update_history: List[Dict[str, Any]] = []
        self.last_check_time = 0
        
        # Callbacks
        self.update_callbacks: List[callable] = []
        
    async def start(self):
        """Start the updater service"""
        try:
            self.logger.info(f"Updater Service started - Current version: {self.current_version}")
            
            # Load update history
            await self._load_update_history()
            
            # Start periodic update checking
            if self.auto_update_enabled:
                asyncio.create_task(self._update_check_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to start updater service: {e}")
            raise
    
    async def stop(self):
        """Stop the updater service"""
        self.logger.info("Updater Service stopped")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="updater_service",
                status=ServiceStatus.HEALTHY,
                version=self.current_version,
                details={
                    "current_version": self.current_version,
                    "auto_update_enabled": self.auto_update_enabled,
                    "auto_install_enabled": self.auto_install_enabled,
                    "last_check": self.last_check_time,
                    "available_update": self.available_update.version if self.available_update else None,
                    "is_checking": self.is_checking,
                    "is_updating": self.is_updating,
                    "update_count": len(self.update_history)
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="updater_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def check_for_updates(self, force: bool = False) -> Optional[UpdateInfo]:
        """Check for available updates"""
        if self.is_checking and not force:
            return self.available_update
        
        try:
            self.is_checking = True
            self.logger.info("Checking for updates...")
            
            # Get latest release info
            release_info = await self._fetch_latest_release()
            
            if release_info:
                latest_version = release_info.get('tag_name', '').lstrip('v')
                
                if self._is_newer_version(latest_version, self.current_version):
                    # Found newer version
                    update_info = UpdateInfo(
                        version=latest_version,
                        download_url=self._get_download_url(release_info),
                        changelog=release_info.get('body', ''),
                        size=self._get_download_size(release_info),
                        checksum=self._get_checksum(release_info),
                        critical=self._is_critical_update(release_info)
                    )
                    
                    self.available_update = update_info
                    self.last_check_time = time.time()
                    
                    self.logger.info(f"Update available: {latest_version}")
                    await self._notify_update_available(update_info)
                    
                    return update_info
                else:
                    self.logger.info("No updates available")
                    self.available_update = None
            
            self.last_check_time = time.time()
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}")
            return None
        finally:
            self.is_checking = False
    
    async def download_update(self, update_info: Optional[UpdateInfo] = None) -> bool:
        """Download an update"""
        if not update_info:
            update_info = self.available_update
        
        if not update_info:
            self.logger.error("No update available to download")
            return False
        
        try:
            self.logger.info(f"Downloading update {update_info.version}...")
            
            # Create download path
            download_filename = f"ai-assistant-{update_info.version}.zip"
            download_path = self.updates_dir / download_filename
            
            # Download file
            success = await self._download_file(update_info.download_url, download_path)
            
            if success:
                # Verify checksum
                if await self._verify_checksum(download_path, update_info.checksum):
                    self.logger.info(f"Update {update_info.version} downloaded successfully")
                    return True
                else:
                    self.logger.error("Update checksum verification failed")
                    download_path.unlink(missing_ok=True)
                    return False
            else:
                self.logger.error("Update download failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error downloading update: {e}")
            return False
    
    async def install_update(self, update_info: Optional[UpdateInfo] = None, 
                           restart_after: bool = True) -> bool:
        """Install an update"""
        if self.is_updating:
            self.logger.warning("Update already in progress")
            return False
        
        if not update_info:
            update_info = self.available_update
        
        if not update_info:
            self.logger.error("No update available to install")
            return False
        
        try:
            self.is_updating = True
            self.logger.info(f"Installing update {update_info.version}...")
            
            # Create backup
            backup_success = await self._create_backup()
            if not backup_success:
                self.logger.error("Failed to create backup - aborting update")
                return False
            
            # Download update if not already downloaded
            download_path = self.updates_dir / f"ai-assistant-{update_info.version}.zip"
            if not download_path.exists():
                download_success = await self.download_update(update_info)
                if not download_success:
                    return False
            
            # Extract and install update
            install_success = await self._install_update_files(download_path, update_info)
            
            if install_success:
                # Record successful update
                await self._record_update(update_info, True)
                
                self.logger.info(f"Update {update_info.version} installed successfully")
                self.current_version = update_info.version
                self.available_update = None
                
                # Notify completion
                await self._notify_update_completed(update_info, True)
                
                # Restart if requested
                if restart_after:
                    await self._restart_application()
                
                return True
            else:
                # Rollback on failure
                self.logger.error("Update installation failed - rolling back")
                await self._rollback_update()
                await self._record_update(update_info, False)
                return False
                
        except Exception as e:
            self.logger.error(f"Error installing update: {e}")
            await self._rollback_update()
            await self._record_update(update_info, False, str(e))
            return False
        finally:
            self.is_updating = False
    
    async def rollback_to_previous_version(self) -> bool:
        """Rollback to the previous version"""
        try:
            self.logger.info("Rolling back to previous version...")
            
            # Find the most recent backup
            backup_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir()]
            if not backup_dirs:
                self.logger.error("No backups available for rollback")
                return False
            
            # Sort by creation time (most recent first)
            backup_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest_backup = backup_dirs[0]
            
            # Restore from backup
            success = await self._restore_from_backup(latest_backup)
            
            if success:
                self.logger.info("Rollback completed successfully")
                # Update current version from backup info
                backup_info_file = latest_backup / "backup_info.json"
                if backup_info_file.exists():
                    with open(backup_info_file, 'r') as f:
                        backup_info = json.load(f)
                        self.current_version = backup_info.get('version', self.current_version)
                
                return True
            else:
                self.logger.error("Rollback failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False
    
    async def _update_check_loop(self):
        """Periodic update checking loop"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check for updates
                update_info = await self.check_for_updates()
                
                # Auto-install if enabled and update is available
                if (update_info and self.auto_install_enabled and 
                    (update_info.critical or self._should_auto_install(update_info))):
                    
                    self.logger.info(f"Auto-installing update {update_info.version}")
                    await self.install_update(update_info, restart_after=False)
                
            except Exception as e:
                self.logger.error(f"Error in update check loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _fetch_latest_release(self) -> Optional[Dict[str, Any]]:
        """Fetch latest release information from update server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.update_server_url}/latest") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"Failed to fetch release info: HTTP {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error fetching release info: {e}")
            return None
    
    def _is_newer_version(self, new_version: str, current_version: str) -> bool:
        """Check if new version is newer than current"""
        try:
            return version.parse(new_version) > version.parse(current_version)
        except Exception:
            # Fallback to string comparison
            return new_version > current_version
    
    def _get_download_url(self, release_info: Dict[str, Any]) -> str:
        """Extract download URL from release info"""
        assets = release_info.get('assets', [])
        
        # Look for platform-specific asset
        platform_name = self._get_platform_name()
        
        for asset in assets:
            asset_name = asset.get('name', '').lower()
            if platform_name in asset_name and asset_name.endswith('.zip'):
                return asset.get('browser_download_url', '')
        
        # Fallback to first zip asset
        for asset in assets:
            if asset.get('name', '').endswith('.zip'):
                return asset.get('browser_download_url', '')
        
        return ''
    
    def _get_download_size(self, release_info: Dict[str, Any]) -> int:
        """Get download size from release info"""
        assets = release_info.get('assets', [])
        if assets:
            return assets[0].get('size', 0)
        return 0
    
    def _get_checksum(self, release_info: Dict[str, Any]) -> str:
        """Get checksum from release info"""
        # Look for checksum in release body or assets
        body = release_info.get('body', '')
        
        # Simple checksum extraction (improve based on your release format)
        import re
        checksum_match = re.search(r'SHA256:\s*([a-fA-F0-9]{64})', body)
        if checksum_match:
            return checksum_match.group(1)
        
        return ''
    
    def _is_critical_update(self, release_info: Dict[str, Any]) -> bool:
        """Check if update is critical"""
        body = release_info.get('body', '').lower()
        name = release_info.get('name', '').lower()
        
        critical_keywords = ['critical', 'security', 'urgent', 'hotfix']
        return any(keyword in body or keyword in name for keyword in critical_keywords)
    
    def _get_platform_name(self) -> str:
        """Get platform name for asset selection"""
        import platform
        system = platform.system().lower()
        
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        else:
            return 'unknown'
    
    async def _download_file(self, url: str, destination: Path) -> bool:
        """Download file from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(destination, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        return True
                    else:
                        self.logger.error(f"Download failed: HTTP {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"Error downloading file: {e}")
            return False
    
    async def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        if not expected_checksum:
            self.logger.warning("No checksum provided - skipping verification")
            return True
        
        try:
            sha256_hash = hashlib.sha256()
            
            async with aiofiles.open(file_path, 'rb') as f:
                async for chunk in f:
                    sha256_hash.update(chunk)
            
            actual_checksum = sha256_hash.hexdigest()
            
            if actual_checksum.lower() == expected_checksum.lower():
                return True
            else:
                self.logger.error(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying checksum: {e}")
            return False
    
    async def _create_backup(self) -> bool:
        """Create backup of current installation"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{self.current_version}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            # Create backup directory
            backup_path.mkdir(exist_ok=True)
            
            # Backup application files
            app_root = Path(__file__).parent.parent.parent
            
            # Copy important files and directories
            important_paths = [
                'backend',
                'frontend/dist',
                'config.json',
                'requirements.txt'
            ]
            
            for path_name in important_paths:
                source_path = app_root / path_name
                if source_path.exists():
                    dest_path = backup_path / path_name
                    
                    if source_path.is_file():
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                    elif source_path.is_dir():
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            
            # Create backup info file
            backup_info = {
                "version": self.current_version,
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "platform": self._get_platform_name()
            }
            
            backup_info_file = backup_path / "backup_info.json"
            with open(backup_info_file, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            self.logger.info(f"Backup created: {backup_path}")
            
            # Clean up old backups (keep last 5)
            await self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return False
    
    async def _install_update_files(self, update_path: Path, update_info: UpdateInfo) -> bool:
        """Install update files"""
        try:
            # Extract update archive
            extract_path = self.temp_dir / f"update_{update_info.version}"
            extract_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(update_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            # Install files
            app_root = Path(__file__).parent.parent.parent
            
            # Copy new files
            for item in extract_path.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(extract_path)
                    dest_path = app_root / relative_path
                    
                    # Create destination directory
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, dest_path)
            
            # Update version info
            version_file = app_root / "version.json"
            version_info = {
                "version": update_info.version,
                "updated_at": datetime.now().isoformat()
            }
            
            with open(version_file, 'w') as f:
                json.dump(version_info, f, indent=2)
            
            # Clean up extraction directory
            shutil.rmtree(extract_path, ignore_errors=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error installing update files: {e}")
            return False
    
    async def _rollback_update(self) -> bool:
        """Rollback failed update"""
        try:
            return await self.rollback_to_previous_version()
        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False
    
    async def _restore_from_backup(self, backup_path: Path) -> bool:
        """Restore from backup"""
        try:
            app_root = Path(__file__).parent.parent.parent
            
            # Restore files from backup
            for item in backup_path.rglob('*'):
                if item.is_file() and item.name != 'backup_info.json':
                    relative_path = item.relative_to(backup_path)
                    dest_path = app_root / relative_path
                    
                    # Create destination directory
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, dest_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring from backup: {e}")
            return False
    
    async def _cleanup_old_backups(self, keep_count: int = 5):
        """Clean up old backups"""
        try:
            backup_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir()]
            
            if len(backup_dirs) > keep_count:
                # Sort by creation time (oldest first)
                backup_dirs.sort(key=lambda x: x.stat().st_mtime)
                
                # Remove oldest backups
                for backup_dir in backup_dirs[:-keep_count]:
                    shutil.rmtree(backup_dir, ignore_errors=True)
                    self.logger.info(f"Removed old backup: {backup_dir.name}")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up backups: {e}")
    
    async def _record_update(self, update_info: UpdateInfo, success: bool, error: str = ""):
        """Record update attempt in history"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "version": update_info.version,
            "success": success,
            "error": error,
            "critical": update_info.critical
        }
        
        self.update_history.append(record)
        
        # Keep history manageable
        if len(self.update_history) > 50:
            self.update_history = self.update_history[-25:]
        
        # Save to file
        await self._save_update_history()
    
    async def _load_update_history(self):
        """Load update history from file"""
        try:
            history_file = self.config.get_data_path("update_history.json")
            if history_file.exists():
                with open(history_file, 'r') as f:
                    self.update_history = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading update history: {e}")
            self.update_history = []
    
    async def _save_update_history(self):
        """Save update history to file"""
        try:
            history_file = self.config.get_data_path("update_history.json")
            with open(history_file, 'w') as f:
                json.dump(self.update_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving update history: {e}")
    
    def _get_current_version(self) -> str:
        """Get current application version"""
        try:
            # Try to read from version file
            version_file = Path(__file__).parent.parent.parent / "version.json"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version_info = json.load(f)
                    return version_info.get('version', '1.0.0')
            
            # Fallback to package version or default
            return '1.0.0'
            
        except Exception:
            return '1.0.0'
    
    def _should_auto_install(self, update_info: UpdateInfo) -> bool:
        """Determine if update should be auto-installed"""
        # Auto-install logic based on update type, user preferences, etc.
        return update_info.critical
    
    async def _notify_update_available(self, update_info: UpdateInfo):
        """Notify about available update"""
        for callback in self.update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback('update_available', update_info)
                else:
                    callback('update_available', update_info)
            except Exception as e:
                self.logger.error(f"Error in update callback: {e}")
    
    async def _notify_update_completed(self, update_info: UpdateInfo, success: bool):
        """Notify about completed update"""
        for callback in self.update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback('update_completed', {'update_info': update_info, 'success': success})
                else:
                    callback('update_completed', {'update_info': update_info, 'success': success})
            except Exception as e:
                self.logger.error(f"Error in update callback: {e}")
    
    async def _restart_application(self):
        """Restart the application"""
        try:
            self.logger.info("Restarting application after update...")
            
            # Platform-specific restart logic
            if sys.platform == "win32":
                subprocess.Popen([sys.executable] + sys.argv)
            else:
                os.execv(sys.executable, [sys.executable] + sys.argv)
                
        except Exception as e:
            self.logger.error(f"Error restarting application: {e}")
    
    def add_update_callback(self, callback: callable):
        """Add update event callback"""
        self.update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: callable):
        """Remove update event callback"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)
    
    def get_update_history(self) -> List[Dict[str, Any]]:
        """Get update history"""
        return self.update_history.copy()
    
    def set_auto_update_enabled(self, enabled: bool):
        """Enable/disable automatic updates"""
        self.auto_update_enabled = enabled
        self.config.set('auto_update_enabled', enabled)
    
    def set_auto_install_enabled(self, enabled: bool):
        """Enable/disable automatic installation"""
        self.auto_install_enabled = enabled
        self.config.set('auto_install_enabled', enabled)
    
    def get_updater_stats(self) -> Dict[str, Any]:
        """Get updater statistics"""
        return {
            "current_version": self.current_version,
            "auto_update_enabled": self.auto_update_enabled,
            "auto_install_enabled": self.auto_install_enabled,
            "last_check_time": self.last_check_time,
            "available_update": self.available_update.version if self.available_update else None,
            "update_history_count": len(self.update_history),
            "backup_count": len([d for d in self.backup_dir.iterdir() if d.is_dir()]),
            "is_checking": self.is_checking,
            "is_updating": self.is_updating
        }