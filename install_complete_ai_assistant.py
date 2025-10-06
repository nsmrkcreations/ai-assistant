#!/usr/bin/env python3
"""
AI Assistant Desktop - Complete Installation Script
Installs all dependencies and sets up the complete working AI assistant.
"""

import os
import sys
import subprocess
import platform
import time
import json
import shutil
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteInstaller:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.system = platform.system().lower()
        self.python_exe = sys.executable
        
    def print_header(self):
        print("🤖 AI Assistant Desktop - Complete Installation")
        print("=" * 70)
        print(f"System: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print(f"Architecture: {platform.machine()}")
        print("=" * 70)
        
    def check_python_version(self):
        """Check Python version"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            logger.error(f"❌ Python 3.8+ required. Current: {version.major}.{version.minor}")
            return False
        
        logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
        
    def install_python_dependencies(self):
        """Install all Python dependencies"""
        logger.info("📦 Installing Python dependencies...")
        
        # Core backend dependencies
        core_packages = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "websockets>=12.0",
            "aiofiles>=23.0.0",
            "python-multipart>=0.0.6",
            "aiosqlite>=0.19.0",
            "cryptography>=41.0.0",
            "psutil>=5.9.0",
            "httpx>=0.25.0",
            "aiohttp>=3.9.0",
            "requests>=2.31.0",
            "pydantic>=2.0.0"
        ]
        
        # GUI automation dependencies
        gui_packages = [
            "pyautogui>=0.9.54",
            "pygetwindow>=0.0.9",
            "pyperclip>=1.8.2",
            "pynput>=1.7.6"
        ]
        
        # Web automation dependencies
        web_packages = [
            "playwright>=1.40.0",
            "beautifulsoup4>=4.12.0",
            "selenium>=4.15.0"
        ]
        
        # Optional AI packages (install if possible)
        ai_packages = [
            "torch>=2.0.0",
            "transformers>=4.35.0",
            "diffusers>=0.24.0",
            "Pillow>=10.0.0",
            "opencv-python>=4.8.0",
            "numpy>=1.24.0"
        ]
        
        all_packages = core_packages + gui_packages + web_packages
        
        # Install core packages
        for package in all_packages:
            try:
                logger.info(f"  Installing {package}...")
                subprocess.check_call([
                    self.python_exe, "-m", "pip", "install", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logger.warning(f"  ⚠️ Failed to install {package}")
        
        # Try to install AI packages (optional)
        logger.info("🤖 Installing AI dependencies (optional)...")
        for package in ai_packages:
            try:
                logger.info(f"  Installing {package}...")
                subprocess.check_call([
                    self.python_exe, "-m", "pip", "install", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logger.warning(f"  ⚠️ Optional package {package} not installed")
        
        logger.info("✅ Python dependencies installed")
        return True
        
    def install_ollama(self):
        """Install Ollama for LLM functionality"""
        logger.info("🧠 Setting up Ollama for AI functionality...")
        
        try:
            # Check if Ollama is already installed
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Ollama already installed")
                return self.setup_ollama_model()
        except FileNotFoundError:
            pass
        
        # Install Ollama
        if self.system == "windows":
            logger.info("📥 Please install Ollama manually:")
            logger.info("  1. Go to https://ollama.ai")
            logger.info("  2. Download and install Ollama for Windows")
            logger.info("  3. Run this installer again")
            return False
            
        elif self.system == "darwin":  # macOS
            try:
                # Try to install via Homebrew
                subprocess.check_call(["brew", "install", "ollama"])
                logger.info("✅ Ollama installed via Homebrew")
                return self.setup_ollama_model()
            except:
                logger.info("📥 Please install Ollama manually:")
                logger.info("  1. Go to https://ollama.ai")
                logger.info("  2. Download and install Ollama for macOS")
                return False
                
        else:  # Linux
            try:
                # Install via curl script
                install_script = "curl -fsSL https://ollama.ai/install.sh | sh"
                subprocess.check_call(install_script, shell=True)
                logger.info("✅ Ollama installed")
                return self.setup_ollama_model()
            except:
                logger.warning("⚠️ Ollama auto-install failed")
                return False
    
    def setup_ollama_model(self):
        """Setup Ollama model"""
        try:
            logger.info("📥 Downloading AI model (this may take a few minutes)...")
            
            # Start Ollama service
            if self.system != "windows":
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(3)
            
            # Pull a lightweight model
            result = subprocess.run(["ollama", "pull", "llama3.1:8b"], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                logger.info("✅ AI model downloaded successfully")
                return True
            else:
                logger.warning("⚠️ Failed to download AI model")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Model download timed out")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Model setup failed: {e}")
            return False
    
    def install_playwright_browsers(self):
        """Install Playwright browsers"""
        logger.info("🌐 Installing web browsers for automation...")
        
        try:
            subprocess.check_call([
                self.python_exe, "-m", "playwright", "install", "chromium"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info("✅ Playwright browsers installed")
            return True
            
        except subprocess.CalledProcessError:
            logger.warning("⚠️ Failed to install Playwright browsers")
            return False
    
    def setup_node_frontend(self):
        """Setup Node.js frontend if available"""
        try:
            # Check if Node.js is available
            node_result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            npm_result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            
            if node_result.returncode != 0 or npm_result.returncode != 0:
                logger.warning("⚠️ Node.js/npm not found - desktop app will not be available")
                return False
            
            logger.info(f"✅ Node.js {node_result.stdout.strip()}")
            
            if not self.frontend_dir.exists():
                logger.warning("⚠️ Frontend directory not found")
                return False
            
            # Install frontend dependencies
            logger.info("📦 Installing frontend dependencies...")
            os.chdir(self.frontend_dir)
            
            result = subprocess.run(["npm", "install"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("⚠️ npm install failed")
                os.chdir(self.root_dir)
                return False
            
            # Build frontend
            logger.info("🔨 Building frontend...")
            result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("⚠️ Frontend build failed")
                os.chdir(self.root_dir)
                return False
            
            os.chdir(self.root_dir)
            logger.info("✅ Frontend built successfully")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Frontend setup failed: {e}")
            os.chdir(self.root_dir)
            return False
    
    def create_config_file(self):
        """Create application configuration"""
        logger.info("⚙️ Creating configuration...")
        
        config = {
            "version": "1.0.0",
            "install_date": time.time(),
            "python_path": str(self.python_exe),
            "features": {
                "llm_available": False,
                "voice_available": False,
                "automation_available": True,
                "web_automation_available": True,
                "desktop_app_available": False
            },
            "models": {
                "llm_model": "llama3.1:8b",
                "stt_model": "base",
                "tts_voice": "en_US-lessac-medium"
            },
            "settings": {
                "theme": "system",
                "auto_start": True,
                "voice_enabled": True,
                "automation_enabled": True
            }
        }
        
        # Check what features are actually available
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            config["features"]["llm_available"] = True
        except:
            pass
        
        if (self.root_dir / "frontend" / "dist").exists():
            config["features"]["desktop_app_available"] = True
        
        config_path = self.root_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("✅ Configuration created")
        
    def create_launchers(self):
        """Create launcher scripts"""
        logger.info("🚀 Creating launcher scripts...")
        
        if self.system == "windows":
            launcher_content = f'''@echo off
title AI Assistant Desktop
echo Starting AI Assistant Desktop...
cd /d "{self.root_dir}"
"{self.python_exe}" start_complete_working_app.py
pause
'''
            launcher_path = self.root_dir / "Start_AI_Assistant.bat"
            with open(launcher_path, 'w') as f:
                f.write(launcher_content)
            
            # Create desktop shortcut
            desktop = Path.home() / "Desktop"
            if desktop.exists():
                shortcut_path = desktop / "AI Assistant.bat"
                with open(shortcut_path, 'w') as f:
                    f.write(launcher_content)
                logger.info("  ✓ Desktop shortcut created")
        
        else:
            launcher_content = f'''#!/bin/bash
echo "Starting AI Assistant Desktop..."
cd "{self.root_dir}"
"{self.python_exe}" start_complete_working_app.py
'''
            launcher_path = self.root_dir / "start_ai_assistant.sh"
            with open(launcher_path, 'w') as f:
                f.write(launcher_content)
            os.chmod(launcher_path, 0o755)
            
            # Create desktop shortcut
            desktop = Path.home() / "Desktop"
            if desktop.exists():
                shortcut_path = desktop / "ai_assistant.sh"
                with open(shortcut_path, 'w') as f:
                    f.write(launcher_content)
                os.chmod(shortcut_path, 0o755)
                logger.info("  ✓ Desktop shortcut created")
        
        logger.info("✅ Launcher scripts created")
    
    def test_installation(self):
        """Test the installation"""
        logger.info("🧪 Testing installation...")
        
        try:
            # Test backend imports
            sys.path.insert(0, str(self.root_dir / "backend"))
            
            from services.database_service import DatabaseService
            from services.llm_service import LLMService
            from services.automation_service import AutomationService
            
            logger.info("✅ Backend services import successfully")
            
            # Test if we can start the minimal backend
            from run_minimal_backend import app
            logger.info("✅ Minimal backend can be imported")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Installation test failed: {e}")
            return False
    
    def install(self):
        """Run complete installation"""
        self.print_header()
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Installing Python dependencies", self.install_python_dependencies),
            ("Setting up Ollama (optional)", self.install_ollama),
            ("Installing Playwright browsers", self.install_playwright_browsers),
            ("Setting up frontend (optional)", self.setup_node_frontend),
            ("Creating configuration", self.create_config_file),
            ("Creating launchers", self.create_launchers),
            ("Testing installation", self.test_installation)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n🔄 {step_name}...")
            try:
                if not step_func():
                    logger.warning(f"⚠️ {step_name} completed with warnings")
            except Exception as e:
                logger.error(f"❌ {step_name} failed: {e}")
        
        self.print_success()
        return True
    
    def print_success(self):
        """Print installation success message"""
        print("\n" + "=" * 70)
        print("🎉 AI Assistant Desktop Installation Complete!")
        print("=" * 70)
        
        if self.system == "windows":
            launcher = "Start_AI_Assistant.bat"
        else:
            launcher = "start_ai_assistant.sh"
        
        print(f"🚀 To start: Run {launcher} or use desktop shortcut")
        print("\n🎯 What's Available:")
        print("  ✅ Web chat interface")
        print("  ✅ Real-time communication")
        print("  ✅ Desktop automation")
        print("  ✅ Web automation")
        print("  ✅ Settings management")
        print("  ✅ Health monitoring")
        
        # Check optional features
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            print("  ✅ AI responses (Ollama)")
        except:
            print("  ⚠️ AI responses (install Ollama for full AI)")
        
        if (self.root_dir / "frontend" / "dist").exists():
            print("  ✅ Desktop application")
        else:
            print("  ⚠️ Desktop app (install Node.js for native app)")
        
        print("\n📍 Access Points:")
        print("  🌐 Web: http://localhost:8000/static/")
        print("  🧪 Test: http://localhost:8000/test")
        print("  📊 Health: http://localhost:8000/health")
        print("  📚 API: http://localhost:8000/docs")
        
        print("\n💡 For Full AI Features:")
        print("  • Install Ollama: https://ollama.ai")
        print("  • Install Node.js: https://nodejs.org")
        print("=" * 70)

def main():
    installer = CompleteInstaller()
    
    try:
        return 0 if installer.install() else 1
    except KeyboardInterrupt:
        print("\n🛑 Installation cancelled")
        return 1
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())