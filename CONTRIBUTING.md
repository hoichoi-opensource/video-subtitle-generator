# Contributing to Video Subtitle Generator

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🚀 Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/Video-subtitle-Generator.git`
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Test with Docker: `docker compose run --rm subtitle-generator`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 🐳 Development Environment

### Prerequisites
- Docker Desktop
- Git
- Text editor/IDE

### Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/Video-subtitle-Generator.git
cd Video-subtitle-Generator

# Create development directories
mkdir -p data/{input,output,config,logs,temp,jobs}

# Add your Google Cloud service account
cp /path/to/service-account.json data/config/

# Run development environment
docker compose run --rm subtitle-generator bash
```

## 🧪 Testing

### Manual Testing
```bash
# Test basic functionality
./docker-run.sh health

# Test with sample video
cp sample.mp4 data/input/
./docker-run.sh --video /data/input/sample.mp4 --languages eng
```

### Automated Testing
```bash
# Run code quality checks
docker compose run --rm subtitle-generator python -m flake8 src/
docker compose run --rm subtitle-generator python -m black --check src/
```

## 📝 Code Standards

### Python Style
- Follow PEP 8
- Use Black for formatting: `black src/`
- Use isort for import sorting: `isort src/`
- Maximum line length: 88 characters

### Documentation
- Add docstrings to all functions and classes
- Update README.md if adding new features
- Include inline comments for complex logic

### Security
- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all user inputs
- Follow security best practices

## 🗂️ Project Structure

```
Video-subtitle-Generator/
├── 📁 .github/           # GitHub templates and workflows
├── 📁 config/            # Configuration files
├── 📁 src/               # Main source code
│   ├── ai_generator.py   # AI/ML processing
│   ├── config_manager.py # Configuration management
│   ├── health_checker.py # Health monitoring
│   └── ...              # Other modules
├── 📁 data/              # Runtime data (gitignored)
├── 🐳 Dockerfile         # Container definition
├── 🐳 docker-compose.yml # Service orchestration
└── 📚 docs/              # Documentation
```

## 🔍 Pull Request Guidelines

### Before Submitting
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Changes are backwards compatible
- [ ] Security implications considered

### PR Description Template
- Clear description of changes
- Link to related issues
- Testing performed
- Breaking changes noted
- Screenshots (if applicable)

## 🐛 Reporting Issues

### Bug Reports
- Use the bug report template
- Include reproduction steps
- Provide environment details
- Include relevant logs

### Feature Requests
- Use the feature request template
- Explain the use case
- Consider implementation complexity
- Discuss alternatives

## 🏗️ Architecture Guidelines

### Adding New Features
1. Consider impact on existing functionality
2. Maintain Docker compatibility
3. Add appropriate error handling
4. Include health checks if relevant
5. Update documentation

### Code Organization
- Keep modules focused and cohesive
- Use dependency injection where appropriate
- Implement proper error handling
- Add comprehensive logging

## 🔒 Security Guidelines

### Data Protection
- Never log sensitive information
- Validate all file paths (prevent directory traversal)
- Sanitize user inputs
- Use secure file permissions

### Dependencies
- Keep dependencies up to date
- Review security advisories
- Use minimal, trusted packages
- Regularly run security scans

## 📊 Performance Considerations

### Optimization
- Profile memory usage
- Optimize video processing pipelines
- Consider parallel processing limits
- Monitor resource consumption

### Testing Performance
- Test with various video sizes
- Monitor memory usage patterns
- Validate processing times
- Check resource cleanup

## 🤝 Community

### Communication
- Be respectful and constructive
- Ask questions in issues or discussions
- Help others when possible
- Follow the code of conduct

### Recognition
Contributors will be recognized in:
- Release notes
- README acknowledgments
- Git commit history

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Questions?** Open an issue or start a discussion. We're here to help! 🎉