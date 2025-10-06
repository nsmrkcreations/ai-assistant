#!/usr/bin/env python3
"""
AI Assistant Desktop - Distribution Package Creator
"""

import os
import sys
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime

class DistributionCreator:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.dist_dir = self.root_dir / "dist"
        self.package_name = "AI-Assistant-Desktop-Minimal"
        
    def create_distribution(self):
        """Create a distribution package"""
        print("📦 Creating AI Assistant Desktop Distribution Package")
        print("=" * 60)
        
        # Clean and create dist directory
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.dist_dir.mkdir(parents=True)
        
        package_dir = self.dist_dir / self.package_name
        package_dir.mkdir()
        
        # Copy essential files
        self.copy_essential_files(package_dir)
        
        # Create package info
        self.create_package_info(package_dir)
        
        # Create README
        self.create_readme(package_dir)
        
        # Create ZIP package
        zip_path = self.create_zip_package()
        
        print(f"\n✅ Distribution package created successfully!")
        print(f"📁 Location: {zip_path}")
        print(f"📊 Size: {self.get_file_size(zip_path)}")
        
        return zip_path
        
    def copy_essential_files(self, package_dir):
        """Copy essential files to package directory"""
        print("📋 Copying essential files...")
        
        # Files to copy
        files_to_copy = [
            "install.py",
            "run_minimal_backend.py", 
            "run_backend_only.py",
            "requirements.txt"
        ]
        
        # Create requirements.txt if it doesn't exist
        requirements_path = self.root_dir / "requirements.txt"
        if not requirements_path.exists():
            with open(requirements_path, 'w') as f:
                f.write("""fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
aiofiles>=23.0.0
python-multipart>=0.0.6
""")
        
        for file_name in files_to_copy:
            src = self.root_dir / file_name
            if src.exists():
                dst = package_dir / file_name
                shutil.copy2(src, dst)
                print(f"  ✓ {file_name}")
        
        # Copy backend directory (minimal version)
        self.copy_backend_minimal(package_dir)
        
        # Copy assets if they exist
        assets_src = self.root_dir / "assets"
        if assets_src.exists():
            assets_dst = package_dir / "assets"
            shutil.copytree(assets_src, assets_dst, ignore=shutil.ignore_patterns('*.psd', '*.ai'))
            print("  ✓ assets/")
            
    def copy_backend_minimal(self, package_dir):
        """Copy minimal backend files"""
        print("🔧 Creating minimal backend...")
        
        backend_dst = package_dir / "backend"
        backend_dst.mkdir()
        
        # Copy static files
        static_src = self.root_dir / "backend" / "static"
        if static_src.exists():
            static_dst = backend_dst / "static"
            shutil.copytree(static_src, static_dst)
            print("  ✓ backend/static/")
        else:
            # Create static directory with index.html
            static_dst = backend_dst / "static"
            static_dst.mkdir()
            
            # Copy the index.html we created earlier
            index_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Assistant Desktop</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; background: #d4edda; color: #155724; }
        .chat { border: 1px solid #ddd; height: 300px; overflow-y: auto; padding: 10px; margin: 10px 0; }
        .input-group { display: flex; gap: 10px; }
        input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Assistant Desktop</h1>
        <div class="status">Backend is running! This is a minimal version for testing.</div>
        <div class="chat" id="chat">
            <div><strong>Assistant:</strong> Hello! I'm ready to help you. This is a minimal version.</div>
        </div>
        <div class="input-group">
            <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    <script>
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;
            
            const chat = document.getElementById('chat');
            chat.innerHTML += `<div><strong>You:</strong> ${message}</div>`;
            chat.innerHTML += `<div><strong>Assistant:</strong> Echo: ${message}</div>`;
            chat.scrollTop = chat.scrollHeight;
            input.value = '';
        }
    </script>
</body>
</html>'''
            
            with open(static_dst / "index.html", 'w', encoding='utf-8') as f:
                f.write(index_content)
            print("  ✓ backend/static/index.html (created)")
            
    def create_package_info(self, package_dir):
        """Create package information file"""
        print("📄 Creating package information...")
        
        info = {
            "name": "AI Assistant Desktop",
            "version": "1.0.0-minimal",
            "description": "A minimal AI assistant desktop application",
            "author": "AI Assistant Team",
            "created": datetime.now().isoformat(),
            "platform": "cross-platform",
            "python_required": "3.8+",
            "dependencies": [
                "fastapi>=0.104.0",
                "uvicorn[standard]>=0.24.0", 
                "websockets>=12.0"
            ],
            "features": [
                "Web-based chat interface",
                "WebSocket real-time communication",
                "Settings management",
                "Health monitoring",
                "Cross-platform compatibility"
            ],
            "installation": {
                "method": "python install.py",
                "requirements": "Python 3.8+ with pip"
            }
        }
        
        with open(package_dir / "package-info.json", 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        print("  ✓ package-info.json")
        
    def create_readme(self, package_dir):
        """Create README file"""
        print("📖 Creating README...")
        
        readme_content = """# AI Assistant Desktop - Minimal Version

🤖 **Your Personal AI Employee - Minimal Distribution**

This is a minimal, standalone version of the AI Assistant Desktop application that runs entirely through a web browser interface.

## ✨ Features

- 💬 **Web Chat Interface**: Clean, modern chat interface
- 🔄 **Real-time Communication**: WebSocket-based messaging
- ⚙️ **Settings Management**: Configurable preferences
- 📊 **Health Monitoring**: System status monitoring
- 🌐 **Cross-platform**: Works on Windows, macOS, and Linux
- 🚀 **No Dependencies**: Minimal Python requirements

## 🚀 Quick Start

### 1. Install
```bash
python install.py
```

### 2. Run
- **Windows**: Double-click `AI_Assistant.bat` on your desktop
- **macOS/Linux**: Run `./ai_assistant.sh` or double-click the desktop shortcut

### 3. Use
- Your browser will open automatically to `http://localhost:8000`
- Start chatting with the AI assistant!

## 📋 Requirements

- **Python 3.8+** with pip
- **Internet connection** (for initial dependency installation)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

## 🔧 Manual Installation

If the automatic installer doesn't work:

```bash
# Install dependencies
pip install fastapi uvicorn[standard] websockets

# Run the backend
python run_backend_only.py

# Open browser to http://localhost:8000
```

## 🌐 Web Interface

The application provides:
- **Main Interface**: `http://localhost:8000/static/`
- **Test Page**: `http://localhost:8000/test`
- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`

## ⚙️ Configuration

Settings are stored in `config.json` and can be modified through the web interface or directly in the file.

## 🔍 Troubleshooting

### Port Already in Use
If port 8000 is busy, edit `run_backend_only.py` and change the port number.

### Dependencies Issues
```bash
pip install --upgrade fastapi uvicorn websockets
```

### Browser Doesn't Open
Manually navigate to `http://localhost:8000/static/`

## 🆙 Upgrading to Full Version

This minimal version can be upgraded to include:
- **Electron Desktop App**: Native desktop application
- **Advanced AI Features**: Local LLM integration, image generation
- **Voice Interface**: Speech-to-text and text-to-speech
- **Automation Tools**: Desktop and web automation
- **Plugin System**: Extensible functionality

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in the terminal/command prompt
3. Ensure Python 3.8+ is installed
4. Verify internet connection for dependency installation

## 📄 License

This software is provided as-is for evaluation and testing purposes.

---

**Enjoy your AI Assistant! 🤖✨**
"""
        
        with open(package_dir / "README.md", 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("  ✓ README.md")
        
    def create_zip_package(self):
        """Create ZIP package"""
        print("🗜️ Creating ZIP package...")
        
        zip_path = self.dist_dir / f"{self.package_name}.zip"
        package_dir = self.dist_dir / self.package_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(self.dist_dir)
                    zipf.write(file_path, arc_path)
                    
        print(f"  ✓ {zip_path.name}")
        return zip_path
        
    def get_file_size(self, file_path):
        """Get human-readable file size"""
        size = file_path.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

def main():
    creator = DistributionCreator()
    
    try:
        zip_path = creator.create_distribution()
        
        print("\n" + "=" * 60)
        print("🎉 Distribution package created successfully!")
        print("=" * 60)
        print(f"📦 Package: {zip_path}")
        print(f"📊 Size: {creator.get_file_size(zip_path)}")
        print("\n📋 To distribute:")
        print("1. Share the ZIP file")
        print("2. Recipients extract and run: python install.py")
        print("3. Application installs and creates desktop shortcuts")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error creating distribution: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())