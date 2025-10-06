# Contributing to AI Assistant Desktop

Thank you for your interest in contributing to AI Assistant Desktop! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- Git
- Basic knowledge of Python, TypeScript, and React

### Development Setup

1. **Fork and Clone**
```bash
git clone https://github.com/your-username/ai-assistant-desktop.git
cd ai-assistant-desktop
```

2. **Setup Backend Environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

3. **Setup Frontend Environment**
```bash
cd frontend
npm install
```

4. **Install Ollama (for LLM functionality)**
```bash
# Follow instructions at https://ollama.ai
ollama pull llama3.1:8b
```

5. **Run Tests**
```bash
# Backend tests
cd backend && python -m pytest

# Frontend tests
cd frontend && npm test
```

## 🏗️ Project Structure

```
ai-assistant-desktop/
├── backend/                 # Python FastAPI backend
│   ├── main.py             # Main application entry
│   ├── services/           # Core services
│   ├── models/             # Data models
│   ├── utils/              # Utilities
│   └── tests/              # Backend tests
├── frontend/               # Electron + React frontend
│   ├── src/
│   │   ├── main/          # Electron main process
│   │   └── renderer/      # React renderer
│   ├── dist/              # Built files
│   └── tests/             # Frontend tests
├── scripts/               # Installation and utility scripts
├── docs/                  # Documentation
└── .kiro/                # Kiro spec files
```

## 🎯 How to Contribute

### 1. Choose an Issue
- Browse [open issues](https://github.com/ai-assistant/desktop/issues)
- Look for issues labeled `good first issue` for beginners
- Comment on the issue to let others know you're working on it

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number
```

### 3. Make Changes
- Follow the coding standards (see below)
- Write tests for new functionality
- Update documentation as needed

### 4. Test Your Changes
```bash
# Run all tests
npm test

# Test specific components
cd backend && python -m pytest tests/test_specific.py
cd frontend && npm test -- --testNamePattern="ComponentName"
```

### 5. Submit a Pull Request
- Push your branch to your fork
- Create a pull request with a clear description
- Link any related issues
- Wait for review and address feedback

## 📝 Coding Standards

### Python (Backend)
- **Style**: Follow PEP 8, use Black formatter
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings
- **Testing**: Write unit tests with pytest

```python
async def process_message(self, message: str, context_id: Optional[str] = None) -> LLMResponse:
    """Process user message and generate response.
    
    Args:
        message: User input message
        context_id: Optional conversation context ID
        
    Returns:
        LLMResponse object with generated response
        
    Raises:
        Exception: If processing fails
    """
    # Implementation here
```

### TypeScript (Frontend)
- **Style**: Use Prettier and ESLint
- **Types**: Prefer interfaces over types
- **Components**: Use functional components with hooks
- **Testing**: Write tests with Jest and React Testing Library

```typescript
interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const MessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
  // Component implementation
};
```

### General Guidelines
- **Commits**: Use conventional commit messages
- **Documentation**: Update README and docs for new features
- **Dependencies**: Minimize new dependencies, justify additions
- **Security**: Follow security best practices

## 🧪 Testing

### Backend Testing
```bash
cd backend

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_llm_service.py

# Run with verbose output
python -m pytest -v
```

### Frontend Testing
```bash
cd frontend

# Run all tests
npm test

# Run in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run specific test
npm test -- --testNamePattern="ChatInterface"
```

### Integration Testing
```bash
# Start backend
cd backend && python main.py &

# Run frontend integration tests
cd frontend && npm run test:integration
```

## 📚 Documentation

### Code Documentation
- **Python**: Use Google-style docstrings
- **TypeScript**: Use JSDoc comments
- **README**: Update for new features
- **API**: Document all endpoints

### Writing Documentation
- Use clear, concise language
- Include code examples
- Add screenshots for UI changes
- Update table of contents

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment Information**
   - OS and version
   - Python version
   - Node.js version
   - AI Assistant version

2. **Steps to Reproduce**
   - Clear, numbered steps
   - Expected vs actual behavior
   - Screenshots if applicable

3. **Logs and Error Messages**
   - Backend logs from `data/logs/`
   - Browser console errors
   - Full error stack traces

## 💡 Feature Requests

For new features:

1. **Check Existing Issues** - Avoid duplicates
2. **Describe the Problem** - What need does this address?
3. **Propose a Solution** - How should it work?
4. **Consider Alternatives** - What other approaches exist?
5. **Additional Context** - Screenshots, mockups, etc.

## 🏷️ Labels and Milestones

### Issue Labels
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `documentation` - Improvements to docs
- `question` - Further information requested

### Priority Labels
- `priority: high` - Critical issues
- `priority: medium` - Important features
- `priority: low` - Nice to have

### Component Labels
- `backend` - Python backend issues
- `frontend` - Electron/React frontend
- `ai` - AI/ML related
- `automation` - Automation features
- `security` - Security related

## 🔄 Release Process

### Version Numbering
We use [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes

### Release Checklist
1. Update version numbers
2. Update CHANGELOG.md
3. Run full test suite
4. Build and test packages
5. Create release notes
6. Tag release
7. Deploy to distribution channels

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn and grow

### Communication
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and collaboration

### Recognition
Contributors are recognized in:
- README.md contributors section
- Release notes
- GitHub contributors page

## 📞 Getting Help

If you need help:

1. **Check Documentation** - README, docs folder
2. **Search Issues** - Someone may have asked before
3. **Ask in Discussions** - Community Q&A
4. **Contact Maintainers** - For urgent issues

## 🎉 Thank You!

Every contribution helps make AI Assistant Desktop better. Whether it's:
- Reporting bugs
- Suggesting features
- Writing code
- Improving documentation
- Helping other users

Your efforts are appreciated! 🙏

---

**Happy Contributing!** 🚀