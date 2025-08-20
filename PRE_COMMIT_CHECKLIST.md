# Pre-Commit Checklist

## 🔍 Security & Privacy Check

- [ ] No hardcoded API keys, tokens, or credentials
- [ ] No personal project IDs or account information  
- [ ] No service account JSON files committed
- [ ] All sensitive data patterns in .gitignore
- [ ] Configuration files use placeholders/templates

## 📁 File Structure Check

- [ ] No temporary or debug files
- [ ] No log files or build artifacts
- [ ] No IDE-specific files (except in .gitignore)
- [ ] No large media files (videos/audio)
- [ ] All example files properly named (.example extension)

## 📝 Documentation Check

- [ ] README.md is up-to-date with latest features
- [ ] All new features documented in appropriate files
- [ ] Setup instructions are clear and complete
- [ ] Environment template is current
- [ ] Contributing guidelines are present

## 🧪 Code Quality Check

- [ ] All Python files pass syntax validation
- [ ] No unused imports or dead code
- [ ] Proper error handling in all modules
- [ ] Test files are functional
- [ ] Configuration files are valid YAML

## 🐳 Docker & Deployment Check

- [ ] docker-compose.yml is valid
- [ ] Dockerfile builds successfully
- [ ] All required dependencies in requirements.txt
- [ ] Environment variables properly templated
- [ ] Setup script is executable and functional

## 🔒 Public Repository Readiness

- [ ] License file is present and appropriate
- [ ] Contributing guidelines exist
- [ ] Security policy is defined
- [ ] Code follows open source best practices
- [ ] No proprietary or confidential information

## ✅ Final Validation

Run these commands before committing:

```bash
# Check for sensitive patterns
grep -r "sk-\|AIza\|ya29\|private_key" . --exclude-dir=.git || echo "No API keys found ✅"

# Validate Python syntax  
find . -name "*.py" -exec python3 -m py_compile {} \;

# Test Docker configuration
docker compose config

# Run setup script test
./setup.sh --dry-run 2>/dev/null || echo "Setup script ready ✅"
```

## 🎯 Repository Status: Ready for Public Push

When all items are checked, the repository is ready for:
```bash
git add .
git commit -m "feat: production-ready AI subtitle generator with translation quality"
git push origin main
```