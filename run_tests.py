#!/usr/bin/env python3
"""
Simple test runner for AI Assistant Desktop Application
"""

import os
import sys
import subprocess
from pathlib import Path

def run_backend_tests():
    """Run backend tests"""
    backend_dir = Path(__file__).parent / "backend"
    
    print("🧪 Running backend tests...")
    
    # Check if pytest is available
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ pytest not found. Installing test dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "tests/requirements-test.txt"], 
                         cwd=backend_dir, check=True)
    except Exception as e:
        print(f"❌ Error checking pytest: {e}")
        return False
    
    # Run tests
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short"
        ], cwd=backend_dir)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running backend tests: {e}")
        return False

def run_frontend_tests():
    """Run frontend tests"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    print("🧪 Running frontend tests...")
    
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("📦 Installing frontend dependencies...")
        try:
            # Try different npm commands based on platform
            npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
            subprocess.run([npm_cmd, "install"], cwd=frontend_dir, check=True)
        except Exception as e:
            print(f"❌ Error installing frontend dependencies: {e}")
            return False
    
    # Run tests
    try:
        # Try different npm commands based on platform
        npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
        result = subprocess.run([
            npm_cmd, "test", "--", "--watchAll=false"
        ], cwd=frontend_dir)
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js and npm.")
        return False
    except Exception as e:
        print(f"❌ Error running frontend tests: {e}")
        return False

def main():
    """Main function"""
    print("🧪 AI Assistant Test Runner")
    print("=" * 30)
    
    backend_success = run_backend_tests()
    frontend_success = run_frontend_tests()
    
    print("\n" + "=" * 30)
    if backend_success and frontend_success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())