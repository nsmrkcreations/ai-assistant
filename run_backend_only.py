#!/usr/bin/env python3
"""
AI Assistant Desktop - Backend Only Runner
Runs just the backend API server for testing
"""

import os
import sys
import asyncio
import logging
import subprocess
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def check_dependencies():
    """Check if required Python packages are available"""
    required_packages = [
        'fastapi', 'uvicorn', 'websockets', 'aiosqlite', 
        'psutil', 'pydantic', 'requests'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing packages: {missing}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True

def main():
    """Main entry point"""
    logger = setup_logging()
    
    print("🚀 AI Assistant Desktop - Backend Only")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Missing dependencies. Please install required packages.")
        return 1
    
    # Change to backend directory
    os.chdir(backend_path)
    
    try:
        # Import and run the backend
        logger.info("Starting backend server...")
        
        # Run the backend main module
        result = subprocess.run([
            sys.executable, "main.py"
        ], cwd=backend_path)
        
        return result.returncode
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        return 0
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())