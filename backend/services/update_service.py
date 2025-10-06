"""
Update Service for automatic updates and version management
"""

import asyncio
import logging
import json
import hashlib
import tempfile
import shutil
import subprocess
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import zipfile
import tarfile

try:
    import httpx
    import packaging.version
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

from models.chat_models import ComponentStatus, ServiceStatus, UpdateInfo
from utils.config import Config

class UpdateService:
    """Service for handling automatic updates"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.current_version = "1.0.0"
        self.update_server_url = "https://api.github.com/repos/ai-assistant/desktop/releases"
        self.last_check = None
        self.available_update: Optional[UpdateInfo] = None
        self.update_in_progress = False
        self.backup_path: Optional[Path] = None
        
    async def start(self):
        """Start the update service"""
        try:
            if not HTTP_AVAILABLE:
                self.logger.warning("HTTP client not available for updates")
                return
            
            # Schedule periodic update checks
            if self.config.updates.auto_update:
                asyncio.create_task(self._periodic_update_check())
            
            self.logger.info("Update Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start update service: {e}")
            raise
    
    async def stop(self):
        """Stop the update service"""
        try:
            if self.update_in_progress:
                self.logger.warning("Update in progress, waiting for completion...")
                # Wait for update to complete or timeout
                timeout = 300  # 5 minutes
                start_time = asyncio.get_event_loop().time()
                while self.update_in_progress and (asyncio.get_event_loop().time() - start_time) < timeout:
                    await asyncio.sleep(1)
            
            self.logger.info("Update Service stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping update service: {e}")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            return ComponentStatus(
                name="update_service",
                status=ServiceStatus.HEALTHY if HTTP_AVAILABLE else ServiceStatus.DEGRADED,
                version=self.current_version,
                details={
                    "http_available": HTTP_AVAILABLE,
                    "current_version": self.current_version,
                    "last_check": self.last_check.isoformat() if self.last_check else None,
                    "available_update": self.available_update.dict() if self.available_update else None,
                    "update_in_progress": self.update_in_progress,
                    "auto_update_enabled": self.config.updates.auto_update
                }
            )
        except Exception as e:
            return ComponentStatus(
                name="update_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def check_for_updates(self) -> Optional[UpdateInfo]:
        """Check for available updates"""
        if not HTTP_AVAILABLE:
            return None
        
        try:
            self.logger.info("Checking for updates...")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.update_server_url,
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Update check failed: HTTP {response.status_code}")
                    return None
                
                releases = response.json()
                
                if not releases:
                    self.logger.info("No releases found")
                    return None
                
                # Get latest release
                latest_release = releases[0]
                latest_version = latest_release["tag_name"].lstrip("v")
                
                # Compare versions
                if self._is_newer_version(latest_version, self.current_version):
                    # Find appropriate asset
                    asset = self._find_suitable_asset(latest_release["assets"])
                    
                    if asset:
                        update_info = UpdateInfo(
                            version=latest_version,
                            release_date=datetime.fromisoformat(
                                latest_release["published_at"].replace("Z", "+00:00")
                            ),
                            description=latest_release["body"] or "No description available",
                            download_url=asset["browser_download_url"],
                            checksum="",  # Would need to be provided separately
                            size=asset["size"],
                            critical=self._is_critical_update(latest_release),
                            changelog=self._parse_changelog(latest_release["body"] or "")
                        )
                        
                        self.available_update = update_info
                        self.last_check = datetime.now()
                        
                        self.logger.info(f"Update available: {latest_version}")
                        return update_info
                    else:
                        self.logger.warning("No suitable asset found for this platform")
                else:
                    self.logger.info("No updates available")
            
            self.last_check = datetime.now()
            return None
            
        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
            return None
    
    async def download_update(self, update_info: UpdateInfo) -> Optional[Path]:
        """Download update package"""
        if not HTTP_AVAILABLE:
            return None
        
        try:
            self.logger.info(f"Downloading update {update_info.version}...")
            
            # Create download directory
            download_dir = self.config.get_temp_path() / "updates"
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine file extension
            url = update_info.download_url
            if url.endswith('.zip'):
                filename = f"update-{update_info.version}.zip"
            elif url.endswith('.tar.gz'):
                filename = f"update-{update_info.version}.tar.gz"
            else:
                filename = f"update-{update_info.version}.bin"
            
            download_path = download_dir / filename
            
            # Download file
            async with httpx.AsyncClient() as client:
                async with client.stream('GET', url, timeout=300.0) as response:
                    if response.status_code != 200:
                        raise Exception(f"Download failed: HTTP {response.status_code}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(download_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Log progress
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                if downloaded % (1024 * 1024) == 0:  # Log every MB
                                    self.logger.info(f"Download progress: {progress:.1f}%")
            
            # Verify download
            if update_info.checksum:
                if not await self._verify_checksum(download_path, update_info.checksum):
                    download_path.unlink()
                    raise Exception("Checksum verification failed")
            
            self.logger.info(f"Update downloaded: {download_path}")
            return download_path
            
        except Exception as e:
            self.logger.error(f"Update download failed: {e}")
            return None
    
    async def install_update(self, update_path: Path, backup: bool = True) -> bool:
        """Install downloaded update"""
        try:
            self.update_in_progress = True
            self.logger.info(f"Installing update from {update_path}")
            
            # Create backup if requested
            if backup and self.config.updates.backup_before_update:
                self.backup_path = await self._create_backup()
                if not self.backup_path:
                    self.logger.error("Failed to create backup, aborting update")
                    return False
            
            # Extract update
            extract_dir = self.config.get_temp_path() / "update_extract"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True)
            
            if not await self._extract_update(update_path, extract_dir):
                self.logger.error("Failed to extract update")
                return False
            
            # Apply update
            if not await self._apply_update(extract_dir):
                self.logger.error("Failed to apply update")
                if self.backup_path:
                    await self._restore_backup()
                return False
            
            # Update version
            self.current_version = self.available_update.version if self.available_update else self.current_version
            self.available_update = None
            
            # Cleanup
            await self._cleanup_update_files(update_path, extract_dir)
            
            self.logger.info("Update installed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Update installation failed: {e}")
            if self.backup_path:
                await self._restore_backup()
            return False
        finally:
            self.update_in_progress = False
    
    async def check_and_update(self) -> Dict[str, Any]:
        """Check for updates and install if available"""
        try:
            # Check for updates
            update_info = await self.check_for_updates()
            
            if not update_info:
                return {"status": "no_update", "message": "No updates available"}
            
            # Download update
            update_path = await self.download_update(update_info)
            
            if not update_path:
                return {"status": "download_failed", "message": "Failed to download update"}
            
            # Install update
            if await self.install_update(update_path):
                return {
                    "status": "updated",
                    "message": f"Successfully updated to version {update_info.version}",
                    "version": update_info.version
                }
            else:
                return {"status": "install_failed", "message": "Failed to install update"}
                
        except Exception as e:
            self.logger.error(f"Update process failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def rollback_update(self) -> bool:
        """Rollback to previous version"""
        if not self.backup_path or not self.backup_path.exists():
            self.logger.error("No backup available for rollback")
            return False
        
        try:
            self.logger.info("Rolling back update...")
            return await self._restore_backup()
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    async def _periodic_update_check(self):
        """Periodic update check task"""
        while True:
            try:
                await asyncio.sleep(self.config.updates.check_interval)
                
                # Check if it's time for an update check
                if (not self.last_check or 
                    datetime.now() - self.last_check > timedelta(seconds=self.config.updates.check_interval)):
                    
                    update_info = await self.check_for_updates()
                    
                    if update_info and self.config.updates.auto_update:
                        # Auto-install non-critical updates
                        if not update_info.critical:
                            await self.check_and_update()
                        else:
                            self.logger.info(f"Critical update available: {update_info.version}")
                            # Critical updates might need user confirmation
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Periodic update check failed: {e}")
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Compare version strings"""
        try:
            if HTTP_AVAILABLE:
                return packaging.version.parse(version1) > packaging.version.parse(version2)
            else:
                # Simple string comparison fallback
                return version1 > version2
        except:
            return False
    
    def _find_suitable_asset(self, assets: List[Dict]) -> Optional[Dict]:
        """Find suitable asset for current platform"""
        import platform
        
        system = platform.system().lower()
        arch = platform.machine().lower()
        
        # Platform-specific asset patterns
        patterns = {
            'windows': ['win', 'windows', '.exe'],
            'darwin': ['mac', 'darwin', 'osx'],
            'linux': ['linux', 'ubuntu', 'debian']
        }
        
        platform_patterns = patterns.get(system, [])
        
        for asset in assets:
            name = asset['name'].lower()
            
            # Check if asset matches platform
            if any(pattern in name for pattern in platform_patterns):
                return asset
        
        # Fallback to first asset
        return assets[0] if assets else None
    
    def _is_critical_update(self, release: Dict) -> bool:
        """Determine if update is critical"""
        body = (release.get('body') or '').lower()
        critical_keywords = ['critical', 'security', 'urgent', 'hotfix', 'vulnerability']
        
        return any(keyword in body for keyword in critical_keywords)
    
    def _parse_changelog(self, body: str) -> List[str]:
        """Parse changelog from release body"""
        lines = body.split('\n')
        changelog = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                changelog.append(line[2:])
            elif line and not line.startswith('#'):
                changelog.append(line)
        
        return changelog[:10]  # Limit to 10 items
    
    async def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            actual_checksum = hasher.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
            
        except Exception as e:
            self.logger.error(f"Checksum verification failed: {e}")
            return False
    
    async def _create_backup(self) -> Optional[Path]:
        """Create backup of current installation"""
        try:
            backup_dir = self.config.get_data_path("backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{self.current_version}_{timestamp}.tar.gz"
            
            # Create backup archive
            app_dir = Path(__file__).parent.parent.parent
            
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(app_dir, arcname='ai_assistant')
            
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            return None
    
    async def _extract_update(self, update_path: Path, extract_dir: Path) -> bool:
        """Extract update package"""
        try:
            if update_path.suffix == '.zip':
                with zipfile.ZipFile(update_path, 'r') as zip_file:
                    zip_file.extractall(extract_dir)
            elif update_path.suffix == '.gz':
                with tarfile.open(update_path, 'r:gz') as tar_file:
                    tar_file.extractall(extract_dir)
            else:
                # Copy as-is for other formats
                shutil.copy2(update_path, extract_dir)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Update extraction failed: {e}")
            return False
    
    async def _apply_update(self, extract_dir: Path) -> bool:
        """Apply extracted update"""
        try:
            app_dir = Path(__file__).parent.parent.parent
            
            # Copy new files
            for item in extract_dir.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(extract_dir)
                    target_path = app_dir / relative_path
                    
                    # Ensure target directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, target_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Update application failed: {e}")
            return False
    
    async def _restore_backup(self) -> bool:
        """Restore from backup"""
        if not self.backup_path or not self.backup_path.exists():
            return False
        
        try:
            app_dir = Path(__file__).parent.parent.parent
            
            # Extract backup
            with tarfile.open(self.backup_path, 'r:gz') as tar:
                tar.extractall(app_dir.parent)
            
            self.logger.info("Backup restored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup restoration failed: {e}")
            return False
    
    async def _cleanup_update_files(self, update_path: Path, extract_dir: Path):
        """Cleanup update files"""
        try:
            if update_path.exists():
                update_path.unlink()
            
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
                
        except Exception as e:
            self.logger.error(f"Update cleanup failed: {e}")
    
    async def get_version_info(self) -> Dict[str, Any]:
        """Get version information"""
        return {
            "current_version": self.current_version,
            "available_update": self.available_update.dict() if self.available_update else None,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "auto_update_enabled": self.config.updates.auto_update
        }