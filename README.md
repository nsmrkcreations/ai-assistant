# AI Assistant Desktop Application

A comprehensive personal AI assistant that operates as a standalone desktop application. It acts as an AI employee capable of voice and text interaction, autonomous task execution, application control, self-healing, and continuous learning from user behavior.

## 🚀 Features

### Core AI Capabilities
- **Voice & Text Interaction**: Natural language processing with Whisper.cpp STT and Piper TTS
- **Intelligent Responses**: Powered by Ollama LLM (Llama 3.1, Mistral, etc.)
- **Context Awareness**: Maintains conversation history and context across sessions

### Automation & Control
- **Application Control**: Launch, control, and automate desktop applications
- **Web Automation**: Browser automation with Playwright for web tasks
- **GUI Automation**: PyAutoGUI integration for desktop interaction
- **File Operations**: Create, manage, and organize files and documents

### Creative Capabilities
- **Image Generation**: AI-powered image creation with Stable Diffusion
- **Video Creation**: Automated video composition and editing
- **Document Generation**: Create presentations, reports, and documents
- **Asset Management**: Organize and manage generated content

### System Intelligence
- **Self-Healing**: Automatic error detection and repair
- **Auto-Updates**: Seamless background updates with rollback capability
- **Learning System**: Adapts to user patterns and preferences
- **Security**: AES-256 encryption and sandboxed execution

### Cross-Platform Support
- **Windows**: Native .exe installer with system integration
- **macOS**: .dmg package with LaunchAgent support
- **Linux**: AppImage and .deb packages with systemd integration

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Electron)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Chat UI     │ │ Voice Input │ │ System Tray             │ │
│  │ (React/TS)  │ │ (WebRTC)    │ │ (Always Available)      │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket/HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ LLM Service │ │ STT Service │ │ TTS Service             │ │
│  │ (Ollama)    │ │ (Whisper)   │ │ (Piper)                 │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Automation  │ │ Learning    │ │ Asset Generation        │ │
│  │ Service     │ │ Service     │ │ (Stable Diffusion)      │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Security    │ │ Watchdog    │ │ Update Service          │ │
│  │ Service     │ │ Service     │ │ (Auto-Updates)          │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- 4GB RAM minimum
- 2GB free disk space

### Quick Install

#### Windows
```bash
# Download and run installer
curl -O https://releases.ai-assistant.com/windows/ai-assistant-setup.exe
ai-assistant-setup.exe
```

#### macOS
```bash
# Download and install
curl -O https://releases.ai-assistant.com/macos/ai-assistant.dmg
open ai-assistant.dmg
```

#### Linux
```bash
# AppImage (Universal)
curl -O https://releases.ai-assistant.com/linux/ai-assistant.AppImage
chmod +x ai-assistant.AppImage
./ai-assistant.AppImage

# Or install .deb package
curl -O https://releases.ai-assistant.com/linux/ai-assistant.deb
sudo dpkg -i ai-assistant.deb
```

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/ai-assistant/desktop.git
cd desktop
```

2. **Setup Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Setup Frontend**
```bash
cd frontend
npm install
npm run build
```

4. **Install Ollama**
```bash
# Install Ollama (https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.1:8b
```

5. **Run the Application**
```bash
# Start backend
cd backend
python main.py

# Start frontend (in development)
cd frontend
npm run dev
```

## 🎯 Usage

### Basic Commands
- **"Open Excel and create a new spreadsheet"**
- **"Generate an image of a sunset over mountains"**
- **"Automate my daily report creation"**
- **"Browse to GitHub and create a new repository"**
- **"Learn my workflow and suggest improvements"**

### Voice Interaction
1. Click the microphone button or use hotkey
2. Speak your command naturally
3. The assistant will transcribe, process, and respond
4. Audio responses are played automatically

### Automation Examples
```python
# The assistant can create complex automations like:
"Every morning at 9 AM, open my email, 
check for urgent messages, create a summary, 
and save it to my daily briefing folder"
```

## 🔧 Configuration

### Models Configuration
```json
{
  "models": {
    "llm_model": "llama3.1:8b",
    "stt_model": "base",
    "tts_voice": "en_US-lessac-medium",
    "image_model": "stable-diffusion-v1-5"
  }
}
```

### Automation Settings
```json
{
  "automation": {
    "enable_gui_automation": true,
    "enable_web_automation": true,
    "safety_checks": true,
    "screenshot_on_error": true
  }
}
```

### Security Settings
```json
{
  "security": {
    "enable_sandboxing": true,
    "require_permissions": true,
    "audit_logging": true,
    "encryption_enabled": true
  }
}
```

## 🔒 Security & Privacy

- **Local Processing**: All AI processing happens locally
- **Encrypted Storage**: AES-256 encryption for all data
- **Sandboxed Execution**: Automation runs in isolated environments
- **Permission System**: Explicit user consent for sensitive operations
- **Audit Logging**: Comprehensive security event tracking
- **No Data Collection**: Your data never leaves your device

## 🤖 AI Models

### Supported LLM Models
- **Llama 3.1** (8B, 70B) - General purpose, highly capable
- **Mistral 7B** - Fast and efficient
- **CodeLlama** - Specialized for coding tasks
- **Custom Models** - Support for custom Ollama models

### Speech Recognition
- **Whisper.cpp** - OpenAI's Whisper models (tiny to large)
- **Local Processing** - No internet required
- **Multi-language** - Support for 50+ languages

### Text-to-Speech
- **Piper TTS** - High-quality neural voices
- **Multiple Voices** - Various accents and styles
- **Real-time** - Low-latency speech synthesis

## 📊 System Monitoring

The application includes comprehensive monitoring:

- **Component Health**: Real-time status of all services
- **Resource Usage**: CPU, memory, and disk monitoring
- **Performance Metrics**: Response times and throughput
- **Error Tracking**: Automatic error detection and reporting
- **Self-Healing**: Automatic recovery from common issues

## 🔄 Updates & Maintenance

### Automatic Updates
- **Background Checks**: Periodic update checking
- **Secure Downloads**: Cryptographically signed updates
- **Rollback Support**: Automatic rollback on failure
- **User Control**: Manual update approval for major versions

### Self-Healing
- **Component Monitoring**: Continuous health checking
- **Automatic Repair**: Fix common issues automatically
- **Dependency Management**: Reinstall missing dependencies
- **Service Recovery**: Restart failed services

## 🎨 Customization

### Themes
- **Light Mode**: Clean, bright interface
- **Dark Mode**: Easy on the eyes
- **System Theme**: Follows OS preference

### Voice Customization
- **Multiple Voices**: Choose from various TTS voices
- **Speed Control**: Adjust speech rate
- **Volume Control**: Per-application audio levels

### Automation Profiles
- **Work Profile**: Office productivity automations
- **Creative Profile**: Design and content creation
- **Developer Profile**: Coding and development tools
- **Custom Profiles**: Create your own automation sets

## 🚨 Troubleshooting

### Common Issues

**Backend won't start**
```bash
# Check Python version
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Ollama status
ollama list
```

**Voice input not working**
- Check microphone permissions
- Verify audio device in system settings
- Test with `python -c "import speech_recognition; print('OK')"`

**Automation failures**
- Verify application permissions
- Check security settings
- Review automation logs in `data/logs/`

### Log Files
- **Application Logs**: `~/.config/ai-assistant/data/logs/`
- **Security Events**: `~/.config/ai-assistant/data/security_events.json`
- **Performance Metrics**: `~/.config/ai-assistant/data/metrics.json`

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style
- **Python**: Black formatter, PEP 8
- **TypeScript**: Prettier, ESLint
- **Documentation**: Clear docstrings and comments

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** - Whisper speech recognition
- **Meta** - Llama language models
- **Stability AI** - Stable Diffusion image generation
- **Ollama** - Local LLM serving
- **Electron** - Cross-platform desktop framework

## 📞 Support

- **Documentation**: [docs.ai-assistant.com](https://docs.ai-assistant.com)
- **Issues**: [GitHub Issues](https://github.com/ai-assistant/desktop/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ai-assistant/desktop/discussions)
- **Email**: support@ai-assistant.com

---

**Made with ❤️ by the AI Assistant Team**