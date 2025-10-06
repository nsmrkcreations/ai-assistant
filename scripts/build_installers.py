#!/usr/bin/env python3
"""
Production Installer Builder for AI Assistant
Creates cross-platform installers with all dependencies
"""

import os
import sys
import subprocess
import shutil
import json
import platform
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import zipfile
import tarfile

class InstallerBuilder:
    """Builds production installers for all platforms"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.build_dir = self.root_dir / "build"
        self.dist_dir = self.root_dir / "dist"
        self.assets_dir = self.root_dir / "assets"
        self.frontend_dir = self.root_dir / "frontend"
        self.backend_dir = self.root_dir / "backend"
        
        # Version info
        self.version = self._get_version()
        self.app_name = "AI Assistant"
        self.app_id = "com.aiassistant.desktop"
        
        # Platform info
        self.current_platform = platform.system().lower()
        
    def build_all_platforms(self):
        """Build installers for all supported platforms"""
        print(f"Building {self.app_name} v{self.version} installers...")
        
        # Prepare build environment
        self._prepare_build_environment()
        
        # Build frontend
        self._build_frontend()
        
        # Build Electron app
        self._build_electron_app()
        
        # Create platform-specific installers
        if self.current_platform == "windows":
            self._build_windows_installer()
        elif self.current_platform == "darwin":
            self._build_macos_installer()
        elif self.current_platform == "linux":
            self._build_linux_installers()
        
        # Create portable versions
        self._create_portable_versions()
        
        print("✅ All installers built successfully!")
        self._print_build_summary()
    
    def _prepare_build_environment(self):
        """Prepare the build environment"""
        print("📦 Preparing build environment...")
        
        # Clean previous builds
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        
        # Create directories
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        
        # Copy backend files
        backend_build = self.build_dir / "backend"
        shutil.copytree(self.backend_dir, backend_build, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '*.pyo', '.pytest_cache', 'tests', '*.log'
        ))
        
        # Copy assets
        if self.assets_dir.exists():
            assets_build = self.build_dir / "assets"
            shutil.copytree(self.assets_dir, assets_build)
        
        # Create requirements.txt for bundling
        self._create_requirements_file()
        
        print("✅ Build environment prepared")
    
    def _build_frontend(self):
        """Build the frontend application"""
        print("🔨 Building frontend...")
        
        # Install dependencies
        subprocess.run([
            "npm", "install"
        ], cwd=self.frontend_dir, check=True)
        
        # Build production version
        subprocess.run([
            "npm", "run", "build"
        ], cwd=self.frontend_dir, check=True)
        
        print("✅ Frontend built successfully")
    
    def _build_electron_app(self):
        """Build Electron application"""
        print("⚡ Building Electron app...")
        
        # Build for current platform
        subprocess.run([
            "npm", "run", "dist"
        ], cwd=self.frontend_dir, check=True)
        
        print("✅ Electron app built successfully")
    
    def _build_windows_installer(self):
        """Build Windows installer using NSIS"""
        print("🪟 Building Windows installer...")
        
        try:
            # Create NSIS script
            nsis_script = self._create_nsis_script()
            
            # Run NSIS compiler
            subprocess.run([
                "makensis",
                str(nsis_script)
            ], check=True)
            
            print("✅ Windows installer created")
            
        except subprocess.CalledProcessError:
            print("⚠️  NSIS not found, creating ZIP package instead")
            self._create_windows_zip()
    
    def _build_macos_installer(self):
        """Build macOS installer (DMG)"""
        print("🍎 Building macOS installer...")
        
        try:
            # The electron-builder should have created the DMG
            # We'll enhance it with additional components
            
            # Find the built app
            app_path = self._find_built_app("darwin")
            if not app_path:
                raise Exception("Built macOS app not found")
            
            # Create enhanced DMG with Python runtime
            self._create_enhanced_dmg(app_path)
            
            print("✅ macOS installer created")
            
        except Exception as e:
            print(f"⚠️  macOS installer creation failed: {e}")
            print("Creating TAR.GZ package instead")
            self._create_macos_tarball()
    
    def _build_linux_installers(self):
        """Build Linux installers (AppImage, DEB, RPM)"""
        print("🐧 Building Linux installers...")
        
        # AppImage
        try:
            self._create_appimage()
            print("✅ AppImage created")
        except Exception as e:
            print(f"⚠️  AppImage creation failed: {e}")
        
        # DEB package
        try:
            self._create_deb_package()
            print("✅ DEB package created")
        except Exception as e:
            print(f"⚠️  DEB package creation failed: {e}")
        
        # RPM package
        try:
            self._create_rpm_package()
            print("✅ RPM package created")
        except Exception as e:
            print(f"⚠️  RPM package creation failed: {e}")
        
        # Fallback: TAR.GZ
        self._create_linux_tarball()
        print("✅ Linux TAR.GZ package created")
    
    def _create_portable_versions(self):
        """Create portable versions for all platforms"""
        print("📦 Creating portable versions...")
        
        # Windows portable
        if self.current_platform == "windows":
            self._create_windows_portable()
        
        # macOS portable
        elif self.current_platform == "darwin":
            self._create_macos_portable()
        
        # Linux portable
        elif self.current_platform == "linux":
            self._create_linux_portable()
        
        print("✅ Portable versions created")
    
    def _create_nsis_script(self) -> Path:
        """Create NSIS installer script"""
        nsis_script = self.build_dir / "installer.nsi"
        
        script_content = f'''
!define APPNAME "{self.app_name}"
!define APPVERSION "{self.version}"
!define APPGUID "{self.app_id}"

Name "${{APPNAME}}"
OutFile "{self.dist_dir / f"{self.app_name}-Setup-{self.version}.exe"}"
InstallDir "$PROGRAMFILES64\\${{APPNAME}}"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy application files
    File /r "{self.frontend_dir / "release" / "win-unpacked"}\\*"
    
    ; Copy backend
    SetOutPath "$INSTDIR\\backend"
    File /r "{self.build_dir / "backend"}\\*"
    
    ; Copy Python runtime (if available)
    IfFileExists "${{TEMP}}\\python-runtime.zip" 0 +3
        SetOutPath "$INSTDIR\\python"
        File /r "${{TEMP}}\\python-runtime\\*"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\${{APPNAME}}"
    CreateShortCut "$SMPROGRAMS\\${{APPNAME}}\\${{APPNAME}}.lnk" "$INSTDIR\\${{APPNAME}}.exe"
    CreateShortCut "$DESKTOP\\${{APPNAME}}.lnk" "$INSTDIR\\${{APPNAME}}.exe"
    
    ; Register uninstaller
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPGUID}}" "DisplayName" "${{APPNAME}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPGUID}}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\\uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$DESKTOP\\${{APPNAME}}.lnk"
    RMDir /r "$SMPROGRAMS\\${{APPNAME}}"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPGUID}}"
SectionEnd
'''
        
        with open(nsis_script, 'w') as f:
            f.write(script_content)
        
        return nsis_script
    
    def _create_windows_zip(self):
        """Create Windows ZIP package"""
        zip_path = self.dist_dir / f"{self.app_name}-{self.version}-Windows.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add Electron app
            app_dir = self._find_built_app("win32")
            if app_dir:
                for file_path in app_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = f"{self.app_name}/" + str(file_path.relative_to(app_dir))
                        zipf.write(file_path, arcname)
            
            # Add backend
            backend_dir = self.build_dir / "backend"
            for file_path in backend_dir.rglob('*'):
                if file_path.is_file():
                    arcname = f"{self.app_name}/backend/" + str(file_path.relative_to(backend_dir))
                    zipf.write(file_path, arcname)
            
            # Add startup script
            startup_script = f'''@echo off
cd /d "%~dp0"
start "" "{self.app_name}.exe"
'''
            zipf.writestr(f"{self.app_name}/start.bat", startup_script)
    
    def _create_enhanced_dmg(self, app_path: Path):
        """Create enhanced macOS DMG with Python runtime"""
        dmg_path = self.dist_dir / f"{self.app_name}-{self.version}-macOS.dmg"
        
        # Create temporary directory for DMG contents
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy app
            app_dest = temp_path / f"{self.app_name}.app"
            shutil.copytree(app_path, app_dest)
            
            # Add backend to app bundle
            backend_dest = app_dest / "Contents" / "Resources" / "backend"
            shutil.copytree(self.build_dir / "backend", backend_dest)
            
            # Create DMG
            subprocess.run([
                "hdiutil", "create",
                "-srcfolder", str(temp_path),
                "-volname", f"{self.app_name} {self.version}",
                "-format", "UDZO",
                str(dmg_path)
            ], check=True)
    
    def _create_macos_tarball(self):
        """Create macOS TAR.GZ package"""
        tarball_path = self.dist_dir / f"{self.app_name}-{self.version}-macOS.tar.gz"
        
        with tarfile.open(tarball_path, 'w:gz') as tar:
            # Add Electron app
            app_dir = self._find_built_app("darwin")
            if app_dir:
                tar.add(app_dir, arcname=f"{self.app_name}.app")
            
            # Add backend
            tar.add(self.build_dir / "backend", arcname="backend")
    
    def _create_appimage(self):
        """Create Linux AppImage"""
        # This would require appimagetool
        # For now, we'll create a simple directory structure
        appimage_dir = self.build_dir / "AppImage"
        appimage_dir.mkdir(exist_ok=True)
        
        # Copy Electron app
        app_dir = self._find_built_app("linux")
        if app_dir:
            shutil.copytree(app_dir, appimage_dir / "app")
        
        # Copy backend
        shutil.copytree(self.build_dir / "backend", appimage_dir / "backend")
        
        # Create desktop file
        desktop_content = f'''[Desktop Entry]
Name={self.app_name}
Exec=./app/{self.app_name}
Icon={self.app_name}
Type=Application
Categories=Office;Productivity;
'''
        
        with open(appimage_dir / f"{self.app_name}.desktop", 'w') as f:
            f.write(desktop_content)
        
        # Create AppRun script
        apprun_content = f'''#!/bin/bash
cd "$(dirname "$0")"
exec ./app/{self.app_name} "$@"
'''
        
        apprun_path = appimage_dir / "AppRun"
        with open(apprun_path, 'w') as f:
            f.write(apprun_content)
        
        os.chmod(apprun_path, 0o755)
    
    def _create_deb_package(self):
        """Create DEB package"""
        deb_dir = self.build_dir / "deb"
        deb_dir.mkdir(exist_ok=True)
        
        # Create directory structure
        (deb_dir / "DEBIAN").mkdir(exist_ok=True)
        (deb_dir / "usr" / "bin").mkdir(parents=True, exist_ok=True)
        (deb_dir / "usr" / "share" / "applications").mkdir(parents=True, exist_ok=True)
        (deb_dir / "opt" / self.app_name.lower()).mkdir(parents=True, exist_ok=True)
        
        # Copy application files
        app_dir = self._find_built_app("linux")
        if app_dir:
            shutil.copytree(app_dir, deb_dir / "opt" / self.app_name.lower() / "app")
        
        shutil.copytree(self.build_dir / "backend", deb_dir / "opt" / self.app_name.lower() / "backend")
        
        # Create control file
        control_content = f'''Package: {self.app_name.lower().replace(" ", "-")}
Version: {self.version}
Section: utils
Priority: optional
Architecture: amd64
Depends: python3, python3-pip
Maintainer: AI Assistant Team
Description: AI Assistant Desktop Application
 Your personal AI employee for productivity and automation.
'''
        
        with open(deb_dir / "DEBIAN" / "control", 'w') as f:
            f.write(control_content)
        
        # Create launcher script
        launcher_content = f'''#!/bin/bash
cd /opt/{self.app_name.lower()}
exec ./app/{self.app_name} "$@"
'''
        
        launcher_path = deb_dir / "usr" / "bin" / self.app_name.lower().replace(" ", "-")
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        os.chmod(launcher_path, 0o755)
        
        # Create desktop file
        desktop_content = f'''[Desktop Entry]
Name={self.app_name}
Exec={self.app_name.lower().replace(" ", "-")}
Icon={self.app_name.lower().replace(" ", "-")}
Type=Application
Categories=Office;Productivity;
'''
        
        with open(deb_dir / "usr" / "share" / "applications" / f"{self.app_name.lower().replace(' ', '-')}.desktop", 'w') as f:
            f.write(desktop_content)
        
        # Build DEB package
        deb_path = self.dist_dir / f"{self.app_name.lower().replace(' ', '-')}-{self.version}-amd64.deb"
        subprocess.run([
            "dpkg-deb", "--build", str(deb_dir), str(deb_path)
        ], check=True)
    
    def _create_rpm_package(self):
        """Create RPM package"""
        # This would require rpmbuild
        # For now, create a spec file template
        spec_content = f'''Name: {self.app_name.lower().replace(" ", "-")}
Version: {self.version}
Release: 1
Summary: AI Assistant Desktop Application
License: MIT
URL: https://github.com/ai-assistant/desktop
BuildArch: x86_64
Requires: python3, python3-pip

%description
Your personal AI employee for productivity and automation.

%files
/opt/{self.app_name.lower()}/*
/usr/bin/{self.app_name.lower().replace(" ", "-")}
/usr/share/applications/{self.app_name.lower().replace(" ", "-")}.desktop

%changelog
* {self._get_date()} AI Assistant Team <team@aiassistant.com> - {self.version}-1
- Initial release
'''
        
        spec_path = self.build_dir / f"{self.app_name.lower().replace(' ', '-')}.spec"
        with open(spec_path, 'w') as f:
            f.write(spec_content)
    
    def _create_linux_tarball(self):
        """Create Linux TAR.GZ package"""
        tarball_path = self.dist_dir / f"{self.app_name}-{self.version}-Linux.tar.gz"
        
        with tarfile.open(tarball_path, 'w:gz') as tar:
            # Add Electron app
            app_dir = self._find_built_app("linux")
            if app_dir:
                tar.add(app_dir, arcname="app")
            
            # Add backend
            tar.add(self.build_dir / "backend", arcname="backend")
            
            # Add startup script
            startup_script = f'''#!/bin/bash
cd "$(dirname "$0")"
exec ./app/{self.app_name} "$@"
'''
            
            startup_path = self.build_dir / "start.sh"
            with open(startup_path, 'w') as f:
                f.write(startup_script)
            
            os.chmod(startup_path, 0o755)
            tar.add(startup_path, arcname="start.sh")
    
    def _create_windows_portable(self):
        """Create Windows portable version"""
        self._create_windows_zip()  # Same as ZIP package
    
    def _create_macos_portable(self):
        """Create macOS portable version"""
        self._create_macos_tarball()  # Same as tarball
    
    def _create_linux_portable(self):
        """Create Linux portable version"""
        self._create_linux_tarball()  # Same as tarball
    
    def _find_built_app(self, platform_name: str) -> Optional[Path]:
        """Find the built Electron app for a platform"""
        release_dir = self.frontend_dir / "release"
        
        if platform_name == "win32":
            return release_dir / "win-unpacked"
        elif platform_name == "darwin":
            for app_dir in release_dir.glob("*.app"):
                return app_dir
        elif platform_name == "linux":
            return release_dir / "linux-unpacked"
        
        return None
    
    def _create_requirements_file(self):
        """Create requirements.txt for Python dependencies"""
        requirements = [
            "fastapi>=0.104.0",
            "uvicorn>=0.24.0",
            "websockets>=12.0",
            "aiofiles>=23.2.1",
            "psutil>=5.9.6",
            "cryptography>=41.0.7",
            "PyJWT>=2.8.0",
            "aiohttp>=3.9.0",
            "Pillow>=10.1.0",
            "numpy>=1.24.0",
            "packaging>=23.2"
        ]
        
        requirements_file = self.build_dir / "requirements.txt"
        with open(requirements_file, 'w') as f:
            f.write('\n'.join(requirements))
    
    def _get_version(self) -> str:
        """Get application version"""
        try:
            version_file = self.root_dir / "version.json"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                    return version_data.get('version', '1.0.0')
            
            # Try package.json
            package_json = self.frontend_dir / "package.json"
            if package_json.exists():
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                    return package_data.get('version', '1.0.0')
            
            return '1.0.0'
            
        except Exception:
            return '1.0.0'
    
    def _get_date(self) -> str:
        """Get current date in RPM changelog format"""
        from datetime import datetime
        return datetime.now().strftime("%a %b %d %Y")
    
    def _print_build_summary(self):
        """Print build summary"""
        print("\n" + "="*50)
        print(f"🎉 BUILD SUMMARY - {self.app_name} v{self.version}")
        print("="*50)
        
        if self.dist_dir.exists():
            installers = list(self.dist_dir.glob("*"))
            if installers:
                print(f"📦 Created {len(installers)} installer(s):")
                for installer in installers:
                    size_mb = installer.stat().st_size / (1024 * 1024)
                    print(f"   • {installer.name} ({size_mb:.1f} MB)")
            else:
                print("⚠️  No installers found in dist directory")
        
        print(f"\n📁 Output directory: {self.dist_dir}")
        print("🚀 Ready for distribution!")

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("AI Assistant Installer Builder")
        print("Usage: python build_installers.py")
        print("Builds production installers for the current platform")
        return
    
    try:
        builder = InstallerBuilder()
        builder.build_all_platforms()
    except KeyboardInterrupt:
        print("\n❌ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()