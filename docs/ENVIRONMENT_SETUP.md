# Environment Setup Guide

This guide will help you set up the AI Web Scraper project environment from scratch. Follow these steps to get your development environment ready.

## 📋 Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **MongoDB 4.4+** - [Download MongoDB](https://www.mongodb.com/try/download/community) or use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **Gemini API Key** - [Get API Key](https://makersuite.google.com/app/apikey)

**Estimated setup time:** 15-20 minutes

---

## 🚀 Quick Start

If you're in a hurry, run these commands:

```bash
# Clone and navigate
git clone <repository-url>
cd traycerTry

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your values
# Set GEMINI_API_KEY=your_actual_api_key_here
# Set MONGODB_URI=mongodb://localhost:27017

# Validate environment
python scripts/preflight_check.py

# Start the application
uvicorn app.main:app --reload
```

---

## 📖 Detailed Setup Instructions

### Step 1: Clone and Navigate

```bash
# Clone the repository
git clone <repository-url>
cd traycerTry

# Verify you're in the correct directory
ls -la  # Should show app/, scripts/, requirements.txt, etc.
```

### Step 2: Python Environment

Create and activate a virtual environment:

**macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (should show venv path)
which python
```

**Windows:**
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify activation
where python
```

**Upgrade pip:**
```bash
pip install --upgrade pip
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list

# Key packages should include:
# - fastapi
# - uvicorn
# - motor
# - google-generativeai
# - pydantic-settings
# - python-dotenv
```

### Step 4: MongoDB Setup

Choose one of the following options:

#### Option A: Local MongoDB Installation

**macOS (using Homebrew):**
```bash
# Install MongoDB
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB service
brew services start mongodb/brew/mongodb-community

# Verify installation
mongosh --version
```

**Ubuntu/Debian:**
```bash
# Import MongoDB public key
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -

# Create list file
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

# Update package database
sudo apt-get update

# Install MongoDB
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Verify installation
mongosh --version
```

**Windows:**
1. Download MongoDB Community Server from [MongoDB Download Center](https://www.mongodb.com/try/download/community)
2. Run the installer and follow the setup wizard
3. MongoDB will start automatically as a Windows service

**Verify local connection:**
```bash
# Connect to MongoDB
mongosh

# Or test connection
mongosh --eval "db.adminCommand('ping')"
```

#### Option B: MongoDB Atlas (Cloud)

1. **Create Atlas Account:**
   - Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Sign up for a free account

2. **Create Cluster:**
   - Click "Create Cluster"
   - Choose "Free" tier (M0)
   - Select your preferred region
   - Click "Create Cluster"

3. **Get Connection String:**
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Copy the connection string (format: `mongodb+srv://username:password@cluster.mongodb.net/`)

4. **Configure Network Access:**
   - Go to "Network Access"
   - Add your IP address or use `0.0.0.0/0` for development (not recommended for production)

5. **Create Database User:**
   - Go to "Database Access"
   - Click "Add New Database User"
   - Create username and password
   - Grant "Read and write to any database" permissions

### Step 5: Gemini API Key

1. **Navigate to Google AI Studio:**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account

2. **Create API Key:**
   - Click "Create API Key"
   - Choose "Create API key in new project" or select existing project
   - Copy the generated API key (format: `AIzaSy...`)

3. **Security Notes:**
   - Keep your API key secure and never commit it to version control
   - The key should be at least 20 characters long
   - Store it in your `.env` file, not in code

### Step 6: Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your favorite editor
nano .env
# or
code .env
# or
vim .env
```

**Configure critical variables:**

```bash
# Required: Your Gemini API key
GEMINI_API_KEY=AIzaSyYourActualApiKeyHere

# Required: MongoDB connection string
# For local MongoDB:
MONGODB_URI=mongodb://localhost:27017

# For MongoDB Atlas:
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Required: Database name
MONGODB_DB=traycer_try

# Optional: Application settings
DEBUG=true
PORT=8000
LOG_LEVEL=INFO
```

**Review other settings in `.env`:**
- `WORKERS`: Number of worker processes (default: 1)
- `CONNECTION_TIMEOUT`: Database connection timeout (default: 30)
- `REQUEST_TIMEOUT`: API request timeout (default: 60)
- `RATE_LIMIT_REQUESTS`: Rate limiting (default: 100)
- `CACHE_TTL`: Cache time-to-live (default: 300)

### Step 7: Validate Environment

```bash
# Quick validation
bash scripts/quick_check.sh

# Full validation
python scripts/preflight_check.py

# Test connections only
python scripts/test_connections.py

# Validate environment variables
python scripts/validate_env.py
```

**Expected output:**
```
🎉 Environment Ready!
All checks passed successfully

Next Steps:
  Start the application: uvicorn app.main:app --reload
  Access API docs: http://localhost:8000/docs
  Check health: curl http://localhost:8000/health
```

### Step 8: Initialize Database

The application will automatically create indexes and run migrations on first startup. Alternatively, you can run them manually:

```bash
# Initialize database indexes
python -m app.database.migrations

# Or start the application (it will initialize automatically)
uvicorn app.main:app --reload
```

---

## ✅ Verification

### Test the Application

1. **Start the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Check health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Access API documentation:**
   - Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser
   - Explore the interactive API documentation

4. **Test scraping endpoint:**
   ```bash
   curl -X POST "http://localhost:8000/scrape" \
        -H "Content-Type: application/json" \
        -d '{"query": "test", "max_results": 5}'
   ```

### Verify All Components

```bash
# Check MongoDB connection
mongosh --eval "db.adminCommand('ping')"

# Check Gemini API (using the test script)
python scripts/test_connections.py --gemini-only

# Check all connections
python scripts/test_connections.py
```

---

## 🔧 Troubleshooting

### Issue: MongoDB Connection Failed

**Symptoms:**
- Error: `MongoDB connection timeout`
- Error: `MongoDB authentication failed`
- Error: `MongoDB network unreachable`

**Solutions:**

1. **Check if MongoDB is running:**
   ```bash
   # macOS/Linux
   brew services list | grep mongodb
   sudo systemctl status mongod
   
   # Windows
   # Check Services in Task Manager or run:
   sc query MongoDB
   ```

2. **Verify connection string format:**
   ```bash
   # Local MongoDB
   MONGODB_URI=mongodb://localhost:27017
   
   # MongoDB Atlas
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
   ```

3. **Check firewall settings:**
   ```bash
   # Test connection
   telnet localhost 27017
   # or
   nc -zv localhost 27017
   ```

4. **For MongoDB Atlas:**
   - Verify IP address is whitelisted
   - Check username and password are correct
   - Ensure cluster is not paused

### Issue: Gemini API Key Invalid

**Symptoms:**
- Error: `GEMINI_API_KEY not configured`
- Error: `Gemini API key invalid`
- Error: `Gemini API quota exceeded`

**Solutions:**

1. **Verify key format:**
   ```bash
   # Check key length and format
   echo $GEMINI_API_KEY | wc -c  # Should be > 20
   echo $GEMINI_API_KEY | head -c 6  # Should start with "AIzaSy"
   ```

2. **Check key in .env file:**
   ```bash
   # Ensure no extra spaces or quotes
   grep GEMINI_API_KEY .env
   ```

3. **Verify API key in Google AI Studio:**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Check if key is active and not expired
   - Verify API is enabled in Google Cloud Console

4. **Check quota limits:**
   - Review usage in Google Cloud Console
   - Consider upgrading plan if needed

### Issue: Import Errors

**Symptoms:**
- Error: `ModuleNotFoundError: No module named 'motor'`
- Error: `ModuleNotFoundError: No module named 'google.generativeai'`

**Solutions:**

1. **Verify virtual environment is activated:**
   ```bash
   which python  # Should show venv path
   pip list      # Should show installed packages
   ```

2. **Reinstall dependencies:**
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

3. **Check Python version:**
   ```bash
   python --version  # Must be 3.8+
   ```

4. **Clear pip cache:**
   ```bash
   pip cache purge
   pip install -r requirements.txt
   ```

### Issue: Permission Denied Errors

**Symptoms:**
- Error: `Permission denied: '/path/to/logs'`
- Error: `Cannot write to log file`

**Solutions:**

1. **Check file permissions:**
   ```bash
   ls -la logs/
   ls -la .env
   ```

2. **Fix permissions:**
   ```bash
   chmod 755 logs/
   chmod 644 .env
   ```

3. **Check write access:**
   ```bash
   touch logs/test.log
   rm logs/test.log
   ```

4. **Run with appropriate user:**
   ```bash
   # Don't run as root unless necessary
   whoami
   ```

### Issue: Port Already in Use

**Symptoms:**
- Error: `Address already in use: Port 8000`
- Error: `Bind failed: Address already in use`

**Solutions:**

1. **Find process using port:**
   ```bash
   # macOS/Linux
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```

2. **Kill the process:**
   ```bash
   # macOS/Linux
   kill -9 <PID>
   
   # Windows
   taskkill /PID <PID> /F
   ```

3. **Use different port:**
   ```bash
   # Change PORT in .env
   PORT=8001
   
   # Or specify port when starting
   uvicorn app.main:app --reload --port 8001
   ```

---

## 📚 Configuration Reference

### Critical Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key | `AIzaSy...` |
| `MONGODB_URI` | ✅ | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DB` | ✅ | Database name | `traycer_try` |

### Application Settings

| Variable | Default | Description | Range |
|----------|---------|-------------|-------|
| `PORT` | `8000` | Server port | 1-65535 |
| `WORKERS` | `1` | Worker processes | 1-32 |
| `DEBUG` | `false` | Debug mode | true/false |
| `LOG_LEVEL` | `INFO` | Logging level | DEBUG/INFO/WARNING/ERROR |

### Performance Settings

| Variable | Default | Description | Range |
|----------|---------|-------------|-------|
| `CONNECTION_TIMEOUT` | `30` | DB connection timeout (s) | 1-300 |
| `REQUEST_TIMEOUT` | `60` | API request timeout (s) | 1-600 |
| `RATE_LIMIT_REQUESTS` | `100` | Requests per window | 1-10000 |
| `CACHE_TTL` | `300` | Cache TTL (s) | 1-3600 |

### Security Settings

| Variable | Default | Description | Values |
|----------|---------|-------------|--------|
| `CORS_ENABLED` | `true` | Enable CORS | true/false |
| `ALLOWED_ORIGINS` | `*` | CORS origins | `origin1,origin2` |
| `ENABLE_METRICS` | `true` | Enable metrics | true/false |

---

## 🔒 Security Considerations

### Development Environment
- ✅ Use `.env` file for local development
- ✅ Never commit `.env` to version control
- ✅ Use strong, unique API keys
- ✅ Limit CORS origins to specific domains
- ✅ Enable debug mode only for development

### Production Environment
- ❌ Never use `.env` file in production
- ✅ Use environment variables or secrets management
- ✅ Use HTTPS with valid SSL certificates
- ✅ Implement proper authentication and authorization
- ✅ Set `DEBUG=false` in production
- ✅ Use production-grade MongoDB instance
- ✅ Monitor API usage and set appropriate rate limits

---

## 🚀 Next Steps

After successful setup:

1. **Explore the API:**
   - Visit [http://localhost:8000/docs](http://localhost:8000/docs)
   - Try the interactive API documentation
   - Test different endpoints

2. **Read the Documentation:**
   - [API Documentation](http://localhost:8000/docs)
   - [Architecture Overview](docs/ARCHITECTURE.md)
   - [Contributing Guidelines](CONTRIBUTING.md)

3. **Run Tests:**
   ```bash
   # Run all tests
   pytest
   
   # Run specific test modules
   pytest tests/test_api.py
   pytest tests/test_scraper.py
   ```

4. **Monitor the Application:**
   ```bash
   # Check health
   curl http://localhost:8000/health
   
   # View logs
   tail -f logs/app.log
   ```

---

## 📞 Support

If you encounter issues not covered in this guide:

1. **Check the logs:**
   ```bash
   tail -f logs/app.log
   ```

2. **Run diagnostics:**
   ```bash
   python scripts/preflight_check.py --verbose
   ```

3. **Review configuration:**
   ```bash
   python scripts/validate_env.py
   ```

4. **Test connections:**
   ```bash
   python scripts/test_connections.py --verbose
   ```

5. **Get help:**
   - Check existing issues in the repository
   - Create a new issue with detailed information
   - Include output from diagnostic commands

---

## 📝 Quick Reference Commands

```bash
# Environment setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Validation
bash scripts/quick_check.sh
python scripts/preflight_check.py
python scripts/test_connections.py

# Application
uvicorn app.main:app --reload
curl http://localhost:8000/health

# Database
mongosh
python -m app.database.migrations

# Testing
pytest
pytest tests/test_api.py -v

# Logs
tail -f logs/app.log
```

---

*Last updated: $(date '+%Y-%m-%d')*
*For the latest version of this guide, check the repository documentation.*
