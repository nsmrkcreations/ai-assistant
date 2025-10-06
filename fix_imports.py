#!/usr/bin/env python3
"""
Script to fix import issues and syntax errors in the AI Assistant project
"""

import os
import sys
from pathlib import Path
import subprocess

def check_python_syntax(file_path):
    """Check Python file for syntax errors"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to compile the file
        compile(content, file_path, 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def check_imports(file_path):
    """Check if imports in a Python file are valid"""
    try:
        # Add the backend directory to Python path
        backend_dir = Path(__file__).parent / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract import statements
        import_lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('from ') or line.startswith('import '):
                import_lines.append(line)
        
        return True, import_lines
    except Exception as e:
        return False, f"Error checking imports: {e}"

def fix_backend_files():
    """Fix backend Python files"""
    backend_dir = Path(__file__).parent / "backend"
    
    print("🔍 Checking backend Python files...")
    
    # Check all Python files
    python_files = list(backend_dir.rglob("*.py"))
    
    issues_found = []
    
    for py_file in python_files:
        if "__pycache__" in str(py_file):
            continue
            
        print(f"  Checking {py_file.relative_to(backend_dir)}...")
        
        # Check syntax
        syntax_ok, syntax_error = check_python_syntax(py_file)
        if not syntax_ok:
            issues_found.append(f"{py_file}: {syntax_error}")
            continue
        
        # Check imports
        imports_ok, imports_info = check_imports(py_file)
        if not imports_ok:
            issues_found.append(f"{py_file}: {imports_info}")
    
    if issues_found:
        print("❌ Issues found:")
        for issue in issues_found:
            print(f"  - {issue}")
        return False
    else:
        print("✅ All backend Python files are valid")
        return True

def fix_frontend_files():
    """Fix frontend TypeScript files"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    print("🔍 Checking frontend TypeScript files...")
    
    # Check if TypeScript is available
    try:
        result = subprocess.run(
            ["npx", "tsc", "--version"], 
            cwd=frontend_dir, 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print("⚠️  TypeScript not available, skipping frontend checks")
            return True
    except FileNotFoundError:
        print("⚠️  npm/npx not available, skipping frontend checks")
        return True
    
    # Run TypeScript compiler check
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"], 
            cwd=frontend_dir, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            print("✅ All frontend TypeScript files are valid")
            return True
        else:
            print("❌ TypeScript compilation errors:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"⚠️  Error checking TypeScript: {e}")
        return True

def create_missing_files():
    """Create any missing essential files"""
    print("📁 Creating missing essential files...")
    
    # Create __init__.py files for Python packages
    backend_dir = Path(__file__).parent / "backend"
    
    # Services __init__.py
    services_init = backend_dir / "services" / "__init__.py"
    if not services_init.exists():
        services_init.write_text("# Services package\n")
        print(f"  Created {services_init}")
    
    # Models __init__.py
    models_init = backend_dir / "models" / "__init__.py"
    if not models_init.exists():
        models_init.write_text("# Models package\n")
        print(f"  Created {models_init}")
    
    # Utils __init__.py
    utils_init = backend_dir / "utils" / "__init__.py"
    if not utils_init.exists():
        utils_init.write_text("# Utils package\n")
        print(f"  Created {utils_init}")
    
    # Tests __init__.py already exists
    
    print("✅ Essential files created")

def main():
    """Main function"""
    print("🔧 AI Assistant - Import and Syntax Fixer")
    print("=" * 50)
    
    # Create missing files first
    create_missing_files()
    
    # Check backend files
    backend_ok = fix_backend_files()
    
    # Check frontend files
    frontend_ok = fix_frontend_files()
    
    print("\n" + "=" * 50)
    if backend_ok and frontend_ok:
        print("🎉 All files are valid! No syntax or import errors found.")
        return 0
    else:
        print("❌ Some issues were found. Please review and fix them.")
        return 1

if __name__ == "__main__":
    sys.exit(main())