#!/usr/bin/env python3
"""
Preflight environment validation script for the AI Web Scraper project.

This script validates the testing environment, checking Python version,
required packages, and optional environment variables. It supports
a --skip-connections flag to avoid testing external service connections.

Usage:
    python scripts/preflight_check.py [--skip-connections]

Options:
    --skip-connections    Skip connection tests to external services
"""

import argparse
import os
import sys
import subprocess
import importlib
from pathlib import Path
from typing import List, Dict, Any


class PreflightChecker:
    """Environment validation and preflight checks."""
    
    def __init__(self, skip_connections: bool = False):
        self.skip_connections = skip_connections
        self.errors = []
        self.warnings = []
        self.project_root = Path(__file__).parent.parent
        
    def run(self) -> int:
        """Run all preflight checks."""
        print("🔍 Running preflight environment validation...")
        
        # Check Python version
        self._check_python_version()
        
        # Check required packages
        self._check_required_packages()
        
        # Check optional environment variables
        self._check_environment_variables()
        
        # Check project structure
        self._check_project_structure()
        
        # Check connections (unless skipped)
        if not self.skip_connections:
            self._check_connections()
        
        # Print results
        self._print_results()
        
        # Return exit code
        return 1 if self.errors else 0
    
    def _check_python_version(self):
        """Check Python version compatibility."""
        print("  🐍 Checking Python version...")
        
        if sys.version_info < (3, 8):
            self.errors.append(f"Python 3.8+ required, found {sys.version}")
        else:
            print(f"    ✅ Python {sys.version.split()[0]} (compatible)")
    
    def _check_required_packages(self):
        """Check required packages are installed."""
        print("  📦 Checking required packages...")
        
        required_packages = [
            'pytest',
            'pytest-asyncio', 
            'pytest-cov',
            'pytest-timeout',
            'fastapi',
            'uvicorn',
            'motor',
            'pydantic',
            'aiohttp',
            'google-generativeai',
            'python-dotenv'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
                print(f"    ✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"    ❌ {package} (missing)")
        
        if missing_packages:
            self.errors.append(f"Missing required packages: {', '.join(missing_packages)}")
            self.errors.append("Install with: pip install -r requirements.txt")
    
    def _check_environment_variables(self):
        """Check optional environment variables."""
        print("  🔧 Checking environment variables...")
        
        env_vars = {
            'GEMINI_API_KEY': 'Required for Gemini API tests',
            'MONGODB_URI': 'Required for MongoDB tests',
            'LOG_LEVEL': 'Optional logging level',
            'AGENT_TIMEOUT_SECONDS': 'Optional agent timeout',
            'SCRAPER_TIMEOUT_SECONDS': 'Optional scraper timeout',
            'PROCESSING_TIMEOUT_SECONDS': 'Optional processing timeout'
        }
        
        for var, description in env_vars.items():
            value = os.getenv(var)
            if value:
                print(f"    ✅ {var} (set)")
            else:
                if var in ['GEMINI_API_KEY', 'MONGODB_URI']:
                    self.warnings.append(f"{var} not set - {description}")
                else:
                    print(f"    ⚠️  {var} (not set - {description})")
    
    def _check_project_structure(self):
        """Check essential project files and directories."""
        print("  📁 Checking project structure...")
        
        essential_paths = [
            'app/',
            'tests/',
            'requirements.txt',
            'pytest.ini',
            'conftest.py',
            'scripts/run_tests.py'
        ]
        
        for path in essential_paths:
            full_path = self.project_root / path
            if full_path.exists():
                print(f"    ✅ {path}")
            else:
                self.errors.append(f"Missing essential path: {path}")
                print(f"    ❌ {path} (missing)")
    
    def _check_connections(self):
        """Check connections to external services."""
        print("  🌐 Checking external service connections...")
        
        # Check MongoDB connection
        mongodb_uri = os.getenv('MONGODB_URI')
        if mongodb_uri:
            if self._test_mongodb_connection(mongodb_uri):
                print("    ✅ MongoDB connection")
            else:
                self.warnings.append("MongoDB connection failed")
                print("    ⚠️  MongoDB connection (failed)")
        else:
            print("    ⚠️  MongoDB connection (skipped - MONGODB_URI not set)")
        
        # Check Gemini API key validity
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key and gemini_key != 'test-api-key-for-ci':
            if self._test_gemini_api_key(gemini_key):
                print("    ✅ Gemini API key")
            else:
                self.warnings.append("Gemini API key validation failed")
                print("    ⚠️  Gemini API key (validation failed)")
        else:
            print("    ⚠️  Gemini API key (skipped - not set or test key)")
    
    def _test_mongodb_connection(self, uri: str) -> bool:
        """Test MongoDB connection."""
        try:
            import motor.motor_asyncio
            import asyncio
            
            async def test_connection():
                client = motor.motor_asyncio.AsyncIOMotorClient(uri)
                try:
                    await client.admin.command('ping')
                    return True
                finally:
                    client.close()
            
            return asyncio.run(test_connection())
        except Exception:
            return False
    
    def _test_gemini_api_key(self, api_key: str) -> bool:
        """Test Gemini API key validity."""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            
            # Try to list models (lightweight operation)
            models = list(genai.list_models())
            return len(models) > 0
        except Exception:
            return False
    
    def _print_results(self):
        """Print validation results."""
        print("\n📊 Preflight Validation Results:")
        
        if not self.errors and not self.warnings:
            print("  ✅ All checks passed!")
            return
        
        if self.warnings:
            print("  ⚠️  Warnings:")
            for warning in self.warnings:
                print(f"    - {warning}")
        
        if self.errors:
            print("  ❌ Errors:")
            for error in self.errors:
                print(f"    - {error}")
        
        print(f"\n{'='*50}")
        if self.errors:
            print("❌ Preflight validation FAILED")
            print("Fix the errors above before running tests.")
        elif self.warnings:
            print("⚠️  Preflight validation PASSED with warnings")
            print("Some tests may be skipped due to missing configuration.")
        else:
            print("✅ Preflight validation PASSED")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Preflight environment validation for AI Web Scraper'
    )
    parser.add_argument(
        '--skip-connections',
        action='store_true',
        help='Skip connection tests to external services'
    )
    
    args = parser.parse_args()
    
    checker = PreflightChecker(skip_connections=args.skip_connections)
    exit_code = checker.run()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()