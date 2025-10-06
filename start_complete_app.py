#!/usr/bin/env python3
"""
Complete AI Assistant Desktop Application Startup Script
This script ensures all components are properly initialized and integrated
"""

import os
import sys
import subprocess
import time
import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional, List
import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIAssistantLauncher:
    """Complete AI Assistant application launcher"""
    
    def __init__(self):
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.processes: List[subprocess.Popen] = []
        self.shutdown_requested = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
        asyncio.create_task(self.shutdown())
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        logger.info("Checking dependencies...")
        
        # Check Python dependencies
        required_python_packages = [
            'fastapi', 'uvicorn', 'websockets', 'aiosqlite', 
            'psutil', 'pydantic', 'requests'
        ]
        
        missing_packages = []
        for package in required_python_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"Missing Python packages: {missing_packages}")
            logger.info("Install with: pip install " + " ".join(missing_packages))
            return False
        
        # Check Node.js and npm
        try:
            subprocess.run(['node', '--version'], check=True, capture_output=True)
            subprocess.run(['npm', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Node.js and npm are required but not found")
            return False
        
        # Check if frontend is built
        frontend_dist = Path('frontend/dist')
        if not frontend_dist.exists():
            logger.warning("Frontend not built, building now...")
            if not self.build_frontend():
                return False
        
        logger.info("All dependencies satisfied")
        return True
    
    def build_frontend(self) -> bool:
        """Build the frontend application"""
        logger.info("Building frontend...")
        
        try:
            # Install frontend dependencies
            subprocess.run(
                ['npm', 'install'], 
                cwd='frontend', 
                check=True,
                capture_output=True
            )
            
            # Build frontend
            subprocess.run(
                ['npm', 'run', 'build'], 
                cwd='frontend', 
                check=True,
                capture_output=True
            )
            
            logger.info("Frontend built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Frontend build failed: {e}")
            return False
    
    def start_backend(self) -> bool:
        """Start the backend service"""
        logger.info("Starting backend service...")
        
        try:
            # Start backend with proper environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path('backend').absolute())
            
            self.backend_process = subprocess.Popen(
                [sys.executable, 'backend/main.py'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(self.backend_process)
            
            # Wait for backend to start
            time.sleep(3)
            
            # Check if backend is running
            if self.backend_process.poll() is None:
                logger.info("Backend service started successfully")
                return True
            else:
                stdout, stderr = self.backend_process.communicate()
                logger.error(f"Backend failed to start: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            return False
    
    def start_frontend(self) -> bool:
        """Start the frontend application"""
        logger.info("Starting frontend application...")
        
        try:
            # Start Electron app
            self.frontend_process = subprocess.Popen(
                ['npm', 'start'],
                cwd='frontend',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(self.frontend_process)
            
            # Wait for frontend to start
            time.sleep(2)
            
            # Check if frontend is running
            if self.frontend_process.poll() is None:
                logger.info("Frontend application started successfully")
                return True
            else:
                stdout, stderr = self.frontend_process.communicate()
                logger.error(f"Frontend failed to start: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start frontend: {e}")
            return False
    
    def check_health(self) -> bool:
        """Check if all components are healthy"""
        try:
            import requests
            
            # Check backend health
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code != 200:
                logger.warning("Backend health check failed")
                return False
            
            # Check if processes are still running
            if self.backend_process and self.backend_process.poll() is not None:
                logger.warning("Backend process has stopped")
                return False
            
            if self.frontend_process and self.frontend_process.poll() is not None:
                logger.warning("Frontend process has stopped")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def monitor_processes(self):
        """Monitor running processes and restart if needed"""
        logger.info("Starting process monitoring...")
        
        while not self.shutdown_requested:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.check_health():
                    logger.warning("Health check failed, attempting restart...")
                    
                    # Restart backend if needed
                    if self.backend_process and self.backend_process.poll() is not None:
                        logger.info("Restarting backend...")
                        self.start_backend()
                    
                    # Restart frontend if needed
                    if self.frontend_process and self.frontend_process.poll() is not None:
                        logger.info("Restarting frontend...")
                        self.start_frontend()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown all processes"""
        logger.info("Shutting down AI Assistant...")
        
        # Stop monitoring
        self.shutdown_requested = True
        
        # Terminate processes gracefully
        for process in self.processes:
            if process and process.poll() is None:
                try:
                    # Try graceful termination first
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        # Force kill if graceful shutdown fails
                        logger.warning(f"Force killing process {process.pid}")
                        process.kill()
                        process.wait()
                        
                except Exception as e:
                    logger.error(f"Error terminating process: {e}")
        
        logger.info("AI Assistant shutdown complete")
    
    async def run(self):
        """Main application runner"""
        logger.info("Starting AI Assistant Desktop Application...")
        
        try:
            # Check dependencies
            if not self.check_dependencies():
                logger.error("Dependency check failed")
                return False
            
            # Start backend
            if not self.start_backend():
                logger.error("Failed to start backend")
                return False
            
            # Start frontend
            if not self.start_frontend():
                logger.error("Failed to start frontend")
                await self.shutdown()
                return False
            
            logger.info("AI Assistant started successfully!")
            logger.info("Backend: http://localhost:8000")
            logger.info("Frontend: Electron application window")
            
            # Start monitoring
            monitor_task = asyncio.create_task(self.monitor_processes())
            
            # Wait for shutdown signal
            while not self.shutdown_requested:
                await asyncio.sleep(1)
            
            # Cancel monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Application startup failed: {e}")
            await self.shutdown()
            return False
    
    def run_sync(self):
        """Synchronous runner for the application"""
        try:
            return asyncio.run(self.run())
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            return True
        except Exception as e:
            logger.error(f"Application error: {e}")
            return False

def main():
    """Main entry point"""
    print("🚀 AI Assistant Desktop Application")
    print("=" * 50)
    
    launcher = AIAssistantLauncher()
    success = launcher.run_sync()
    
    if success:
        print("\n✅ AI Assistant shutdown successfully")
        sys.exit(0)
    else:
        print("\n❌ AI Assistant failed to start or encountered an error")
        sys.exit(1)

if __name__ == "__main__":
    main()