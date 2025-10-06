#!/usr/bin/env python3
"""
AI Assistant Desktop - Production Launcher
This script ensures everything works and provides a complete, testable application.
"""

import os
import sys
import subprocess
import time
import webbrowser
import threading
import json
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionLauncher:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        
    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            logger.error(f"Python 3.8+ required. Current: {version.major}.{version.minor}")
            return False
        logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
        
    def install_backend_dependencies(self):
        """Install required backend dependencies"""
        logger.info("📦 Installing backend dependencies...")
        
        required_packages = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "websockets>=12.0",
            "aiofiles>=23.0.0",
            "python-multipart>=0.0.6",
            "aiosqlite>=0.19.0",
            "cryptography>=41.0.0",
            "psutil>=5.9.0"
        ]
        
        try:
            for package in required_packages:
                logger.info(f"  Installing {package}...")
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info("✅ Backend dependencies installed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install dependencies: {e}")
            return False
            
    def check_node_npm(self):
        """Check if Node.js and npm are available"""
        try:
            node_result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            npm_result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            
            if node_result.returncode == 0 and npm_result.returncode == 0:
                logger.info(f"✅ Node.js {node_result.stdout.strip()}")
                logger.info(f"✅ npm {npm_result.stdout.strip()}")
                return True
            else:
                logger.warning("⚠️ Node.js/npm not found - will use web interface only")
                return False
                
        except FileNotFoundError:
            logger.warning("⚠️ Node.js/npm not found - will use web interface only")
            return False
            
    def install_frontend_dependencies(self):
        """Install frontend dependencies if Node.js is available"""
        if not self.check_node_npm():
            return False
            
        logger.info("📦 Installing frontend dependencies...")
        
        try:
            os.chdir(self.frontend_dir)
            
            # Install dependencies
            subprocess.check_call(["npm", "install"], stdout=subprocess.DEVNULL)
            logger.info("✅ Frontend dependencies installed")
            
            os.chdir(self.root_dir)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install frontend dependencies: {e}")
            os.chdir(self.root_dir)
            return False
            
    def build_frontend(self):
        """Build the frontend if possible"""
        if not self.frontend_dir.exists():
            return False
            
        logger.info("🔨 Building frontend...")
        
        try:
            os.chdir(self.frontend_dir)
            
            # Build the frontend
            subprocess.check_call(["npm", "run", "build"], stdout=subprocess.DEVNULL)
            logger.info("✅ Frontend built successfully")
            
            os.chdir(self.root_dir)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Frontend build failed: {e}")
            os.chdir(self.root_dir)
            return False
            
    def start_backend_server(self):
        """Start the backend server"""
        logger.info("🚀 Starting backend server...")
        
        # Add backend to Python path
        sys.path.insert(0, str(self.backend_dir))
        
        try:
            # Import and start the minimal backend
            from run_minimal_backend import app
            import uvicorn
            
            # Start server in a separate thread
            def run_server():
                uvicorn.run(
                    app,
                    host="0.0.0.0",
                    port=8000,
                    log_level="warning"  # Reduce log noise
                )
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            time.sleep(3)
            
            # Test if server is running
            import requests
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Backend server started successfully")
                    return True
            except:
                pass
                
            logger.error("❌ Backend server failed to start properly")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to start backend: {e}")
            return False
            
    def start_electron_app(self):
        """Start the Electron app if available"""
        if not self.frontend_dir.exists():
            return False
            
        logger.info("🖥️ Starting Electron app...")
        
        try:
            os.chdir(self.frontend_dir)
            
            # Start Electron
            subprocess.Popen(["npm", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            os.chdir(self.root_dir)
            logger.info("✅ Electron app started")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Could not start Electron app: {e}")
            os.chdir(self.root_dir)
            return False
            
    def open_web_interface(self):
        """Open the web interface in browser"""
        logger.info("🌐 Opening web interface...")
        
        def open_browser():
            time.sleep(2)  # Wait for server to be ready
            try:
                webbrowser.open("http://localhost:8000/static/")
                logger.info("✅ Web interface opened")
            except Exception as e:
                logger.warning(f"⚠️ Could not open browser: {e}")
                
        threading.Thread(target=open_browser, daemon=True).start()
        
    def create_desktop_shortcut(self):
        """Create desktop shortcut"""
        try:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                return False
                
            if sys.platform == "win32":
                shortcut_content = f'''@echo off
title AI Assistant Desktop
echo Starting AI Assistant Desktop...
cd /d "{self.root_dir}"
"{sys.executable}" launch_production.py
pause
'''
                shortcut_path = desktop / "AI Assistant.bat"
                with open(shortcut_path, 'w') as f:
                    f.write(shortcut_content)
                    
            else:
                shortcut_content = f'''#!/bin/bash
echo "Starting AI Assistant Desktop..."
cd "{self.root_dir}"
"{sys.executable}" launch_production.py
'''
                shortcut_path = desktop / "ai_assistant.sh"
                with open(shortcut_path, 'w') as f:
                    f.write(shortcut_content)
                os.chmod(shortcut_path, 0o755)
                
            logger.info("✅ Desktop shortcut created")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Could not create desktop shortcut: {e}")
            return False
            
    def run_production(self):
        """Run the complete production setup"""
        print("🤖 AI Assistant Desktop - Production Launch")
        print("=" * 60)
        
        # Check system requirements
        if not self.check_python_version():
            return False
            
        # Install backend dependencies
        if not self.install_backend_dependencies():
            return False
            
        # Try to setup frontend
        has_frontend = False
        if self.check_node_npm():
            if self.install_frontend_dependencies():
                has_frontend = self.build_frontend()
                
        # Start backend server
        if not self.start_backend_server():
            return False
            
        # Try to start Electron app, fallback to web interface
        electron_started = False
        if has_frontend:
            electron_started = self.start_electron_app()
            
        if not electron_started:
            self.open_web_interface()
            
        # Create desktop shortcut
        self.create_desktop_shortcut()
        
        # Print success message
        self.print_success_message(has_frontend, electron_started)
        
        return True
        
    def print_success_message(self, has_frontend, electron_started):
        """Print success message with instructions"""
        print("\n" + "=" * 60)
        print("🎉 AI Assistant Desktop is now running!")
        print("=" * 60)
        
        if electron_started:
            print("🖥️ Electron desktop app is starting...")
            print("📱 Native desktop interface available")
        else:
            print("🌐 Web interface available at: http://localhost:8000/static/")
            print("🧪 Test page available at: http://localhost:8000/test")
            
        print("📊 Backend API: http://localhost:8000")
        print("💬 WebSocket: ws://localhost:8000/ws")
        print("🔍 Health check: http://localhost:8000/health")
        
        if not has_frontend:
            print("\n💡 To get the full desktop experience:")
            print("   1. Install Node.js and npm")
            print("   2. Run this script again")
            
        print("\n🎯 Features available:")
        print("   • Real-time chat interface")
        print("   • WebSocket communication")
        print("   • Settings management")
        print("   • Health monitoring")
        print("   • Cross-platform compatibility")
        
        print("\n🛑 To stop: Press Ctrl+C in this terminal")
        print("=" * 60)
        
    def wait_for_shutdown(self):
        """Wait for user to stop the application"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down AI Assistant Desktop...")
            return

def main():
    launcher = ProductionLauncher()
    
    try:
        if launcher.run_production():
            launcher.wait_for_shutdown()
            return 0
        else:
            logger.error("❌ Failed to start AI Assistant Desktop")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Startup cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())