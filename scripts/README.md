# Scripts Directory

This directory contains validation and utility scripts for the AI Web Scraper project. These scripts help ensure proper environment setup, test connections, and provide diagnostic capabilities.

## 📋 Overview

The scripts directory provides comprehensive environment validation and troubleshooting tools:

- **Environment Validation**: Check `.env` configuration and variable formats
- **Connection Testing**: Verify MongoDB and Gemini API connectivity
- **Pre-flight Checks**: Comprehensive validation before starting the application
- **Quick Validation**: Fast environment checks for development
- **Interactive Fixes**: Help resolve common configuration issues

## 🔧 Available Scripts

### validate_env.py

**Purpose**: Validate environment variables in `.env` file

**Usage**:
```bash
python scripts/validate_env.py
python scripts/validate_env.py --verbose
python scripts/validate_env.py --project-root /path/to/project
```

**What it checks**:
- `.env` file existence and format
- Required variables presence (`GEMINI_API_KEY`, `MONGODB_URI`, `MONGODB_DB`)
- Variable format validation (API key format, MongoDB URI format, etc.)
- Configuration completeness compared to `.env.example`
- Boolean, integer, float, and list value validation

**Exit codes**:
- `0` - All validations passed
- `1` - Critical failures found

**Example output**:
```
🔍 Environment Validation Report
==================================================
✅ .env file exists
✅ Found 45 environment variables
✅ GEMINI_API_KEY format is valid
✅ MONGODB_URI format is valid
✅ MONGODB_DB format is valid

📊 Validation Summary
==================================================
✅ Passed: 8
⚠️  Warnings: 2
❌ Errors: 0

Total checks: 10
🎉 All validations passed!
```

### test_connections.py

**Purpose**: Test MongoDB and Gemini API connectivity

**Usage**:
```bash
python scripts/test_connections.py
python scripts/test_connections.py --mongodb-only
python scripts/test_connections.py --gemini-only
python scripts/test_connections.py --verbose --timeout 10
```

**What it checks**:
- MongoDB connection with ping test
- Database accessibility and collection listing
- Gemini API authentication and response
- Connection latency measurement
- Error categorization and troubleshooting

**Exit codes**:
- `0` - All connections successful
- `1` - Connection failures

**Example output**:
```
🔗 Connection Test Report
==================================================
ℹ️  Testing MongoDB connection...
✅ MongoDB connected successfully (45.23ms)
ℹ️  Testing Gemini API connection...
✅ Gemini API connected successfully (1234.56ms)

📊 Connection Summary
==================================================
✅ MongoDB: Connected (45.23ms)
   Database: traycer_try
   Collections: 5
✅ Gemini API: Connected (1234.56ms)
   Response: OK

Results: 2/2 connections successful
🎉 All connections successful!
```

### preflight_check.py

**Purpose**: Comprehensive pre-flight validation before starting application

**Usage**:
```bash
python scripts/preflight_check.py
python scripts/preflight_check.py --skip-connections
python scripts/preflight_check.py --ci --json-output report.json
python scripts/preflight_check.py --verbose --fix-permissions
```

**What it checks**:
- **Phase 1**: Environment validation (all checks from `validate_env.py`)
- **Phase 2**: Dependency check (required Python packages)
- **Phase 3**: Connection tests (MongoDB and Gemini API)
- **Phase 4**: Configuration validation (value ranges and conflicts)
- **Phase 5**: File system check (directories, permissions, Python files)

**Exit codes**:
- `0` - All checks passed, ready to start
- `1` - Critical failures, cannot start
- `2` - Warnings present, can start but may have issues

**Example output**:
```
🚀 Pre-flight Check Report
============================================================
Project: traycerTry
Timestamp: 2024-01-01 12:00:00
System: Darwin 24.6.0

Phase 1: Environment Validation
============================================================
✅ Environment validation passed

Phase 2: Dependency Check
============================================================
✅ All required packages are installed

Phase 3: Connection Tests
============================================================
✅ All connections successful

Phase 4: Configuration Validation
============================================================
✅ Configuration validation passed

Phase 5: File System Check
============================================================
✅ File system check passed

📊 Final Summary
============================================================
🎉 Environment Ready!
All checks passed successfully

Statistics:
  Total checks: 25
  Passed: 25
  Failed: 0
  Warnings: 0
  Duration: 3.45s

🚀 Next Steps:
  Start the application: uvicorn app.main:app --reload
  Access API docs: http://localhost:8000/docs
  Check health: curl http://localhost:8000/health
```

### quick_check.sh

**Purpose**: Fast environment validation for development

**Usage**:
```bash
bash scripts/quick_check.sh
bash scripts/quick_check.sh --full
bash scripts/quick_check.sh --fix
bash scripts/quick_check.sh --help
```

**What it checks**:
- `.env` file existence
- Python 3.8+ version
- Virtual environment activation
- `requirements.txt` existence
- MongoDB running on localhost:27017
- `GEMINI_API_KEY` configuration
- Required Python packages

**Exit codes**:
- `0` - Environment ready
- `1` - Issues found

**Example output**:
```
🔍 Quick Environment Check
==============================
Project: traycerTry
Time: 2024-01-01 12:00:00

Basic Checks:
✅ .env file exists
✅ Python 3.11.0 (OK)
✅ Virtual environment active: venv
✅ requirements.txt exists

Service Checks:
✅ MongoDB running on localhost:27017
✅ GEMINI_API_KEY is configured

Package Checks:
✅ All required packages are installed

Environment Validation:
✅ Environment validation passed

📊 Quick Check Summary
=========================
🎉 Environment is ready!
All critical checks passed

Next Steps:
  Start server: uvicorn app.main:app --reload
  Access docs: http://localhost:8000/docs
  Check health: curl http://localhost:8000/health
```

### fix_env.py

**Purpose**: Interactive tool to fix environment configuration issues

**Usage**:
```bash
python scripts/fix_env.py
python scripts/fix_env.py --auto
python scripts/fix_env.py --interactive
python scripts/fix_env.py --backup-only
python scripts/fix_env.py --restore backup.env
```

**What it does**:
- Creates `.env` from `.env.example` if missing
- Prompts for missing required variables with validation
- Fixes common formatting issues (boolean values, whitespace)
- Creates backup before making changes
- Tests configuration after fixes
- Provides guided setup for first-time users

**Exit codes**:
- `0` - Environment fixed successfully
- `1` - Cannot fix or user cancelled

**Example output**:
```
🔧 Environment Configuration Fixer
==================================================
Project: traycerTry
Mode: Interactive

⚠️  .env file not found
Create .env from .env.example? (y/n) [y]: y
✅ Created .env from .env.example

⚠️  GEMINI_API_KEY needs configuration
Get your API key from: https://makersuite.google.com/app/apikey
Enter your Gemini API key: AIzaSyYourActualApiKeyHere
✅ GEMINI_API_KEY configured

⚠️  MONGODB_URI needs configuration
Common MongoDB URIs:
  Local: mongodb://localhost:27017
  Atlas: mongodb+srv://username:password@cluster.mongodb.net/
  Docker: mongodb://mongodb:27017
Enter MongoDB URI [mongodb://localhost:27017]: 
✅ MONGODB_URI configured

📊 Changes Made
==============================
1. Created .env file
2. Configured GEMINI_API_KEY
3. Configured MONGODB_URI

💾 Backup created: .env.backup.20240101_120000
   To restore: python scripts/fix_env.py --restore .env.backup.20240101_120000

✅ Guided setup completed successfully
```

## 🔄 Workflow Recommendations

### First-time Setup
```bash
# 1. Fix environment configuration
python scripts/fix_env.py

# 2. Run comprehensive validation
python scripts/preflight_check.py

# 3. Start the application
uvicorn app.main:app --reload
```

### Daily Development
```bash
# Quick validation before starting work
bash scripts/quick_check.sh

# If issues found, fix them
python scripts/fix_env.py

# Start development
uvicorn app.main:app --reload
```

### Before Deployment
```bash
# Run strict validation for CI/CD
python scripts/preflight_check.py --ci --json-output preflight_report.json

# Check exit code
echo $?  # Should be 0 for success
```

### Troubleshooting
```bash
# Step 1: Validate environment
python scripts/validate_env.py

# Step 2: Test connections
python scripts/test_connections.py

# Step 3: Run comprehensive check
python scripts/preflight_check.py --verbose

# Step 4: Check logs if needed
tail -f logs/app.log
```

## 🔧 Integration with CI/CD

### GitHub Actions Example

```yaml
name: Environment Validation
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Validate environment
        run: python scripts/preflight_check.py --ci
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          MONGODB_URI: ${{ secrets.MONGODB_URI }}
          MONGODB_DB: traycer_try_test
```

### GitLab CI Example

```yaml
validate_environment:
  stage: test
  image: python:3.11
  before_script:
    - pip install -r requirements.txt
  script:
    - python scripts/preflight_check.py --ci --json-output validation_report.json
  artifacts:
    reports:
      junit: validation_report.json
    paths:
      - validation_report.json
  only:
    - merge_requests
    - main
```

## 💡 Development Tips

### Adding New Validation Checks

1. **Extend `validate_env.py`**:
   ```python
   def validate_new_variable(self, key: str, value: str) -> bool:
       """Validate new variable format."""
       # Add validation logic
       if not value:
           self.errors.append(f"{key} is required")
           return False
       # ... validation logic
       return True
   ```

2. **Update validation rules**:
   ```python
   # In validate_variable_formats method
   if key in new_variable_list:
       self.validate_new_variable(key, value)
   ```

3. **Test the validation**:
   ```bash
   python scripts/validate_env.py --verbose
   ```

### Extending Connection Tests

1. **Add new service test**:
   ```python
   async def test_new_service(self) -> Dict[str, Any]:
       """Test new service connection."""
       result = {
           "service": "New Service",
           "status": "unknown",
           "latency_ms": None,
           "error": None
       }
       # ... test logic
       return result
   ```

2. **Include in test suite**:
   ```python
   # In test_all_connections method
   tasks.append(self.test_new_service())
   ```

### Contributing Improvements

1. **Follow existing patterns**:
   - Use consistent error handling
   - Include proper exit codes
   - Add verbose output options
   - Provide helpful error messages

2. **Test your changes**:
   ```bash
   # Test individual script
   python scripts/your_script.py --verbose
   
   # Test integration
   python scripts/preflight_check.py
   ```

3. **Update documentation**:
   - Add new options to this README
   - Update usage examples
   - Include error scenarios

## 🐛 Common Issues and Solutions

### Script Import Errors
```bash
# Error: ModuleNotFoundError
# Solution: Ensure you're in project root
cd /path/to/traycerTry
python scripts/validate_env.py
```

### Permission Denied
```bash
# Error: Permission denied
# Solution: Make script executable
chmod +x scripts/quick_check.sh
```

### Environment File Not Found
```bash
# Error: .env file not found
# Solution: Copy from example
cp env.example .env
# Or use fix script
python scripts/fix_env.py
```

### Connection Timeouts
```bash
# Error: Connection timeout
# Solution: Check service status
# MongoDB: brew services list | grep mongodb
# Or: systemctl status mongod
# Then: python scripts/test_connections.py --verbose
```

## 📚 Additional Resources

- [Environment Setup Guide](../docs/ENVIRONMENT_SETUP.md)
- [Main README](../README.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Google Gemini API](https://ai.google.dev/)

## 🤝 Contributing

When contributing to the scripts:

1. **Follow the existing code style**
2. **Add comprehensive error handling**
3. **Include verbose output options**
4. **Update this documentation**
5. **Test with different scenarios**
6. **Ensure backward compatibility**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

*For questions or issues with the scripts, please check the troubleshooting section above or create an issue in the repository.*
