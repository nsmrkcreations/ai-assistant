#!/usr/bin/env python3
"""
AI Assistant Desktop Application Startup Script
Simple script to start the application with proper environment setup
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import json

class AIAssistantLauncher:
    """Launcher for AI Assistant Desktop Application"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        print("🔍 Checking dependencies...")
        
        # Check Python
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ required")
            return False
        
        # Check if backend dependencies are installed
        try:
            import fastapi
            import uvicorn
            print("✅ Backend dependencies found")
        except ImportError:
            print("❌ Backend dependencies missing. Run: pip install -r backend/requirements.txt")
            return False
        
        # Check if Node.js is available
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Node.js found")
            else:
                print("❌ Node.js not found")
                return False
        except FileNotFoundError:
            print("❌ Node.js not found")
            return False
        
        # Check if frontend is built
        if not (self.frontend_dir / "dist").exists():
            print("⚠️  Frontend not built. Building now...")
            return self.build_frontend()
        
        return True
    
    def build_frontend(self):
        """Build the frontend application"""
        try:
            print("📦 Installing frontend dependencies...")
            result = subprocess.run(
                ["npm", "install"], 
                cwd=self.frontend_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to install frontend dependencies: {result.stderr}")
                return False
            
            print("🔨 Building frontend...")
            result = subprocess.run(
                ["npm", "run", "build"], 
                cwd=self.frontend_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to build frontend: {result.stderr}")
                return False
            
            print("✅ Frontend built successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error building frontend: {e}")
            return False
    
    def start_backend(self):
        """Start the backend server"""
        print("🚀 Starting backend server...")
        
        try:
            # Start backend server
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=self.backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                print("✅ Backend server started successfully")
                return process
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Backend server failed to start:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting backend: {e}")
            return None
    
    def start_frontend(self):
        """Start the frontend application"""
        print("🖥️  Starting frontend application...")
        
        try:
            # Start Electron app
            process = subprocess.Popen(
                ["npm", "start"],
                cwd=self.frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return process
            
        except Exception as e:
            print(f"❌ Error starting frontend: {e}")
            return None
    
    def run(self):
        """Run the complete application"""
        print("🤖 AI Assistant Desktop Application")
        print("=" * 40)
        
        # Check dependencies
        if not self.check_dependencies():
            print("\n❌ Dependency check failed. Please install missing dependencies.")
            return 1
        
        # Start backend
        backend_process = self.start_backend()
        if not backend_process:
            print("\n❌ Failed to start backend server.")
            return 1
        
        try:
            # Start frontend
            frontend_process = self.start_frontend()
            if not frontend_process:
                print("\n❌ Failed to start frontend application.")
                backend_process.terminate()
                return 1
            
            print("\n🎉 AI Assistant is now running!")
            print("📱 The application window should open automatically.")
            print("🔗 Backend API: http://localhost:8000")
            print("⏹️  Press Ctrl+C to stop the application")
            
            # Wait for processes
            try:
                frontend_process.wait()
            except KeyboardInterrupt:
                print("\n⏹️  Stopping AI Assistant...")
            
        finally:
            # Cleanup processes
            try:
                if backend_process and backend_process.poll() is None:
                    backend_process.terminate()
                    backend_process.wait(timeout=5)
            except:
                pass
            
            try:
                if 'frontend_process' in locals() and frontend_process.poll() is None:
                    frontend_process.terminate()
                    frontend_process.wait(timeout=5)
            except:
                pass
        
        print("👋 AI Assistant stopped.")
        return 0

def main():
    """Main entry point"""
    launcher = AIAssistantLauncher()
    return launcher.run()

if __name__ == "__main__":
    sys.exit(main())