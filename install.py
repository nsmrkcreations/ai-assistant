#!/usr/bin/env python3
"""
AI Assistant Desktop - Installation Script
"""

import os
import sys
import subprocess
import platform
import shutil
import zipfile
import json
from pathlib import Path

class AIAssistantInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.python_exe = sys.executable
        self.install_dir = Path.home() / "AIAssistant"
        self.current_dir = Path(__file__).parent
        
    def print_header(self):
        print("🤖 AI Assistant Desktop - Installation")
        print("=" * 50)
        print(f"System: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print(f"Install Directory: {self.install_dir}")
        print("=" * 50)
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ Python 3.8 or higher is required")
            print(f"Current version: {version.major}.{version.minor}.{version.micro}")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
        
    def install_dependencies(self):
        """Install required Python packages"""
        print("📦 Installing Python dependencies...")
        
        packages = [
            "fastapi",
            "uvicorn[standard]",
            "websockets",
            "aiofiles",
            "python-multipart"
        ]
        
        try:
            for package in packages:
                print(f"  Installing {package}...")
                subprocess.check_call([
                    self.python_exe, "-m", "pip", "install", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print("✅ All dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
            
    def create_install_directory(self):
        """Create installation directory and copy files"""
        print(f"📁 Creating installation directory: {self.install_dir}")
        
        try:
            # Create directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy essential files
            files_to_copy = [
                "run_minimal_backend.py",
                "run_backend_only.py",
                "backend/static/index.html"
            ]
            
            for file_path in files_to_copy:
                src = self.current_dir / file_path
                if src.exists():
                    dst = self.install_dir / file_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    print(f"  Copied: {file_path}")
            
            # Copy backend directory if it exists
            backend_src = self.current_dir / "backend"
            if backend_src.exists():
                backend_dst = self.install_dir / "backend"
                if backend_dst.exists():
                    shutil.rmtree(backend_dst)
                shutil.copytree(backend_src, backend_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'tests'))
                print("  Copied: backend directory")
            
            print("✅ Installation directory created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create installation directory: {e}")
            return False
            
    def create_launcher_scripts(self):
        """Create launcher scripts for different platforms"""
        print("🚀 Creating launcher scripts...")
        
        try:
            if self.system == "windows":
                self.create_windows_launcher()
            else:
                self.create_unix_launcher()
                
            print("✅ Launcher scripts created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create launcher scripts: {e}")
            return False
            
    def create_windows_launcher(self):
        """Create Windows batch file launcher"""
        launcher_content = f'''@echo off
title AI Assistant Desktop
echo Starting AI Assistant Desktop...
cd /d "{self.install_dir}"
"{self.python_exe}" run_backend_only.py
pause
'''
        
        launcher_path = self.install_dir / "AI_Assistant.bat"
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_content)
            
        # Create desktop shortcut
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            shortcut_path = desktop / "AI Assistant.bat"
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write(launcher_content)
            print("  Created desktop shortcut")
            
    def create_unix_launcher(self):
        """Create Unix shell script launcher"""
        launcher_content = f'''#!/bin/bash
echo "Starting AI Assistant Desktop..."
cd "{self.install_dir}"
"{self.python_exe}" run_backend_only.py
'''
        
        launcher_path = self.install_dir / "ai_assistant.sh"
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_content)
        
        # Make executable
        os.chmod(launcher_path, 0o755)
        
        # Try to create desktop shortcut
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            shortcut_path = desktop / "ai_assistant.sh"
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write(launcher_content)
            os.chmod(shortcut_path, 0o755)
            print("  Created desktop shortcut")
            
    def create_config_file(self):
        """Create configuration file"""
        print("⚙️ Creating configuration file...")
        
        config = {
            "version": "1.0.0",
            "install_date": str(Path.ctime(Path.now())),
            "python_path": str(self.python_exe),
            "install_path": str(self.install_dir),
            "backend_port": 8000,
            "auto_open_browser": True,
            "theme": "light"
        }
        
        config_path = self.install_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        print("✅ Configuration file created")
        
    def test_installation(self):
        """Test if installation works"""
        print("🧪 Testing installation...")
        
        try:
            # Test if we can import the main modules
            test_script = f'''
import sys
sys.path.insert(0, "{self.install_dir}")
from run_minimal_backend import app
print("✅ Backend imports successfully")
'''
            
            result = subprocess.run([
                self.python_exe, "-c", test_script
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ Installation test passed")
                return True
            else:
                print(f"❌ Installation test failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Installation test error: {e}")
            return False
            
    def install(self):
        """Run the complete installation process"""
        self.print_header()
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Installing dependencies", self.install_dependencies),
            ("Creating installation directory", self.create_install_directory),
            ("Creating launcher scripts", self.create_launcher_scripts),
            ("Creating configuration", self.create_config_file),
            ("Testing installation", self.test_installation)
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            if not step_func():
                print(f"\n❌ Installation failed at: {step_name}")
                return False
                
        self.print_success()
        return True
        
    def print_success(self):
        """Print installation success message"""
        print("\n" + "=" * 50)
        print("🎉 AI Assistant Desktop installed successfully!")
        print("=" * 50)
        print(f"📁 Installation directory: {self.install_dir}")
        
        if self.system == "windows":
            launcher = "AI_Assistant.bat"
        else:
            launcher = "ai_assistant.sh"
            
        print(f"🚀 To start the application, run: {self.install_dir / launcher}")
        print("🌐 Or check your desktop for a shortcut")
        print("\nThe application will:")
        print("  • Start a web server on http://localhost:8000")
        print("  • Open your browser automatically")
        print("  • Provide a chat interface to test the AI assistant")
        print("\n💡 This is a minimal version. For full features, install:")
        print("  • Node.js and npm (for the Electron frontend)")
        print("  • PyTorch (for AI image generation)")
        print("  • Whisper.cpp (for speech recognition)")
        print("=" * 50)

def main():
    installer = AIAssistantInstaller()
    
    try:
        success = installer.install()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Installation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error during installation: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())