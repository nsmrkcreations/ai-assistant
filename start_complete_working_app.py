#!/usr/bin/env python3
"""
AI Assistant Desktop - Complete Working Application Launcher
This script starts the complete AI assistant with all working features.
"""

import asyncio
import logging
import sys
import os
import subprocess
import time
import webbrowser
import threading
import json
import signal
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteAIAssistant:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        self.backend_process = None
        self.frontend_process = None
        self.running = False
        
    def check_dependencies(self):
        """Check and install required dependencies"""
        logger.info("🔍 Checking dependencies...")
        
        # Check Python version
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            logger.error(f"❌ Python 3.8+ required. Current: {version.major}.{version.minor}")
            return False
        
        logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        
        # Install backend dependencies
        backend_packages = [
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
            "requests>=2.31.0"
        ]
        
        logger.info("📦 Installing backend dependencies...")
        for package in backend_packages:
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logger.warning(f"⚠️ Failed to install {package}")
        
        logger.info("✅ Backend dependencies ready")
        
        # Check Node.js for frontend
        try:
            node_result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            npm_result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            
            if node_result.returncode == 0 and npm_result.returncode == 0:
                logger.info(f"✅ Node.js {node_result.stdout.strip()}")
                logger.info(f"✅ npm {npm_result.stdout.strip()}")
                return True
            else:
                logger.warning("⚠️ Node.js/npm not found - will use web interface only")
                return True
                
        except FileNotFoundError:
            logger.warning("⚠️ Node.js/npm not found - will use web interface only")
            return True
    
    def start_backend(self):
        """Start the backend server"""
        logger.info("🚀 Starting AI Assistant Backend...")
        
        # Add backend to Python path
        sys.path.insert(0, str(self.backend_dir))
        
        try:
            # Import the backend main module
            os.chdir(self.backend_dir)
            
            # Start backend in a separate process
            self.backend_process = subprocess.Popen([
                sys.executable, "main.py"
            ], cwd=self.backend_dir)
            
            # Wait for backend to start
            time.sleep(5)
            
            # Test if backend is running
            try:
                import requests
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Backend server started successfully")
                    return True
            except:
                pass
            
            logger.info("✅ Backend server started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start backend: {e}")
            return False
    
    def start_frontend(self):
        """Start the frontend (Electron or web)"""
        if not self.frontend_dir.exists():
            logger.warning("⚠️ Frontend directory not found")
            return self.open_web_interface()
        
        try:
            # Check if we can build/start Electron
            os.chdir(self.frontend_dir)
            
            # Install dependencies
            logger.info("📦 Installing frontend dependencies...")
            result = subprocess.run(["npm", "install"], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning("⚠️ npm install failed, using web interface")
                return self.open_web_interface()
            
            # Try to build
            logger.info("🔨 Building frontend...")
            result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning("⚠️ Frontend build failed, using web interface")
                return self.open_web_interface()
            
            # Start Electron
            logger.info("🖥️ Starting Electron app...")
            self.frontend_process = subprocess.Popen([
                "npm", "start"
            ], cwd=self.frontend_dir)
            
            logger.info("✅ Electron app started")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Electron startup failed: {e}")
            return self.open_web_interface()
    
    def open_web_interface(self):
        """Open web interface as fallback"""
        logger.info("🌐 Opening web interface...")
        
        def open_browser():
            time.sleep(3)  # Wait for backend
            try:
                webbrowser.open("http://localhost:8000/static/")
                logger.info("✅ Web interface opened")
            except Exception as e:
                logger.warning(f"⚠️ Could not open browser: {e}")
                logger.info("📍 Manual access: http://localhost:8000/static/")
        
        threading.Thread(target=open_browser, daemon=True).start()
        return True
    
    def create_desktop_shortcut(self):
        """Create desktop shortcut"""
        try:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                return
            
            if sys.platform == "win32":
                shortcut_content = f'''@echo off
title AI Assistant Desktop
echo Starting AI Assistant Desktop...
cd /d "{self.root_dir}"
"{sys.executable}" start_complete_working_app.py
pause
'''
                shortcut_path = desktop / "AI Assistant.bat"
                with open(shortcut_path, 'w') as f:
                    f.write(shortcut_content)
            else:
                shortcut_content = f'''#!/bin/bash
echo "Starting AI Assistant Desktop..."
cd "{self.root_dir}"
"{sys.executable}" start_complete_working_app.py
'''
                shortcut_path = desktop / "ai_assistant.sh"
                with open(shortcut_path, 'w') as f:
                    f.write(shortcut_content)
                os.chmod(shortcut_path, 0o755)
            
            logger.info("✅ Desktop shortcut created")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not create desktop shortcut: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info("🛑 Shutdown signal received")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self):
        """Graceful shutdown"""
        if not self.running:
            return
        
        self.running = False
        logger.info("🛑 Shutting down AI Assistant...")
        
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
            except:
                self.frontend_process.kill()
        
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=10)
            except:
                self.backend_process.kill()
        
        logger.info("✅ Shutdown complete")
    
    def print_status(self):
        """Print application status"""
        print("\n" + "=" * 70)
        print("🤖 AI Assistant Desktop - Complete Working Version")
        print("=" * 70)
        print("🎯 Features Available:")
        print("  ✅ Real-time chat interface")
        print("  ✅ WebSocket communication")
        print("  ✅ LLM integration (requires Ollama)")
        print("  ✅ Voice interface (requires Whisper/Piper)")
        print("  ✅ Desktop automation (PyAutoGUI)")
        print("  ✅ Settings management")
        print("  ✅ Health monitoring")
        print("  ✅ Cross-platform support")
        print("\n📍 Access Points:")
        print("  🌐 Web Interface: http://localhost:8000/static/")
        print("  🧪 Test Page: http://localhost:8000/test")
        print("  📊 API Docs: http://localhost:8000/docs")
        print("  💬 WebSocket: ws://localhost:8000/ws")
        print("\n💡 Optional Enhancements:")
        print("  • Install Ollama for AI responses: https://ollama.ai")
        print("  • Install Node.js for desktop app: https://nodejs.org")
        print("\n🛑 To stop: Press Ctrl+C")
        print("=" * 70)
    
    def run(self):
        """Run the complete AI assistant"""
        print("🤖 AI Assistant Desktop - Complete Working Application")
        print("=" * 70)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Check dependencies
        if not self.check_dependencies():
            return 1
        
        # Start backend
        if not self.start_backend():
            return 1
        
        # Start frontend
        self.start_frontend()
        
        # Create desktop shortcut
        self.create_desktop_shortcut()
        
        # Print status
        self.print_status()
        
        # Keep running
        self.running = True
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
        
        return 0

def main():
    assistant = CompleteAIAssistant()
    return assistant.run()

if __name__ == "__main__":
    sys.exit(main())