#!/usr/bin/env python3
"""
Environment validation script for AI Web Scraper project.

This script validates the .env file against .env.example and performs
comprehensive checks on environment variables including format validation,
required variable presence, and configuration completeness.

Usage:
    python scripts/validate_env.py

Exit codes:
    0 - All validations passed
    1 - Critical failures found
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import argparse


class Colors:
    """Terminal color codes for output formatting."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class EnvValidator:
    """Environment validation class."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.env_file = project_root / '.env'
        self.env_example_file = project_root / '.env.example'
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        
    def print_status(self, message: str, status: str = "info"):
        """Print colored status message."""
        if status == "success":
            print(f"{Colors.GREEN}✅ {message}{Colors.END}")
        elif status == "error":
            print(f"{Colors.RED}❌ {message}{Colors.END}")
        elif status == "warning":
            print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
        elif status == "info":
            print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")
        else:
            print(f"   {message}")
    
    def check_file_existence(self) -> bool:
        """Check if .env file exists."""
        if not self.env_file.exists():
            self.errors.append(f".env file not found at {self.env_file}")
            self.print_status(f".env file not found at {self.env_file}", "error")
            self.print_status("Copy .env.example to .env and configure your values", "info")
            return False
        
        self.passed.append(".env file exists")
        self.print_status(".env file exists", "success")
        return True
    
    def parse_env_file(self, file_path: Path) -> Dict[str, str]:
        """Parse environment file and return key-value pairs."""
        env_vars = {}
        if not file_path.exists():
            return env_vars
            
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove inline comments (split on # only when not inside quotes)
                    if '#' in value:
                        # Simple approach: find # that's not inside quotes
                        in_quotes = False
                        quote_char = None
                        comment_pos = -1
                        
                        for i, char in enumerate(value):
                            if char in ['"', "'"] and (i == 0 or value[i-1] != '\\'):
                                if not in_quotes:
                                    in_quotes = True
                                    quote_char = char
                                elif char == quote_char:
                                    in_quotes = False
                                    quote_char = None
                            elif char == '#' and not in_quotes:
                                comment_pos = i
                                break
                        
                        if comment_pos != -1:
                            value = value[:comment_pos].strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
                else:
                    self.warnings.append(f"Invalid line format in {file_path.name}:{line_num}: {line}")
        
        return env_vars
    
    def extract_required_vars_from_example(self) -> Dict[str, str]:
        """Extract required variables from .env.example."""
        required_vars = {}
        if not self.env_example_file.exists():
            return required_vars
            
        with open(self.env_example_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Consider variables required if they don't have default values
                    # or are marked as required in comments
                    if not value or value in ['', 'your_value_here', 'your_api_key_here', 'your_database_name']:
                        required_vars[key] = value
                    elif '# Required' in line or '# REQUIRED' in line:
                        required_vars[key] = value
        
        return required_vars
    
    def validate_gemini_api_key(self, api_key: str) -> bool:
        """Validate Gemini API key format."""
        if not api_key:
            self.errors.append("GEMINI_API_KEY is empty")
            return False
        
        if api_key == "gemini_api_key" or api_key == "your_api_key_here":
            self.errors.append("GEMINI_API_KEY is using placeholder value")
            return False
        
        if len(api_key) < 20:
            self.errors.append("GEMINI_API_KEY is too short (minimum 20 characters)")
            return False
        
        if not api_key.startswith("AIzaSy"):
            self.warnings.append("GEMINI_API_KEY doesn't start with expected prefix 'AIzaSy'")
        
        self.passed.append("GEMINI_API_KEY format is valid")
        return True
    
    def validate_mongodb_uri(self, uri: str) -> bool:
        """Validate MongoDB URI format."""
        if not uri:
            self.errors.append("MONGODB_URI is empty")
            return False
        
        if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
            self.errors.append("MONGODB_URI must start with 'mongodb://' or 'mongodb+srv://'")
            return False
        
        self.passed.append("MONGODB_URI format is valid")
        return True
    
    def validate_mongodb_db(self, db_name: str) -> bool:
        """Validate MongoDB database name."""
        if not db_name:
            self.errors.append("MONGODB_DB is empty")
            return False
        
        # Check for valid database name characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', db_name):
            self.errors.append("MONGODB_DB contains invalid characters (use alphanumeric, underscore, hyphen)")
            return False
        
        self.passed.append("MONGODB_DB format is valid")
        return True
    
    def validate_boolean(self, key: str, value: str) -> bool:
        """Validate boolean value."""
        if value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
            self.errors.append(f"{key} has invalid boolean value: {value}")
            return False
        
        self.passed.append(f"{key} boolean format is valid")
        return True
    
    def validate_integer(self, key: str, value: str) -> bool:
        """Validate integer value."""
        try:
            int(value)
            self.passed.append(f"{key} integer format is valid")
            return True
        except ValueError:
            self.errors.append(f"{key} has invalid integer value: {value}")
            return False
    
    def validate_float(self, key: str, value: str) -> bool:
        """Validate float value."""
        try:
            float(value)
            self.passed.append(f"{key} float format is valid")
            return True
        except ValueError:
            self.errors.append(f"{key} has invalid float value: {value}")
            return False
    
    def validate_list(self, key: str, value: str) -> bool:
        """Validate comma-separated list value."""
        if not value:
            self.warnings.append(f"{key} is empty")
            return True
        
        # Basic validation - check for reasonable list format
        if ',' in value:
            items = [item.strip() for item in value.split(',')]
            if any(not item for item in items):
                self.warnings.append(f"{key} contains empty list items")
        
        self.passed.append(f"{key} list format is valid")
        return True
    
    def validate_by_pattern(self, key: str, value: str) -> bool:
        """Validate variable format by inferring type from patterns."""
        if not value:
            return True
        
        # Infer boolean from common patterns
        if key.upper().startswith(('ENABLE_', 'DISABLE_', 'USE_', 'ALLOW_', 'REQUIRE_')):
            return self.validate_boolean(key, value)
        
        # Infer integer from common patterns
        if any(pattern in key.upper() for pattern in ['_SIZE', '_COUNT', '_LIMIT', '_TIMEOUT', '_SECONDS', '_MS', '_DAYS', '_MB', '_GB']):
            return self.validate_integer(key, value)
        
        # Infer float from common patterns
        if any(pattern in key.upper() for pattern in ['_THRESHOLD', '_RATE', '_DELAY', '_TEMPERATURE', '_SCORE']):
            return self.validate_float(key, value)
        
        # Infer list from common patterns
        if any(pattern in key.upper() for pattern in ['_ORIGINS', '_HOSTS', '_PROXIES', '_ENDPOINTS', '_KEYS']):
            return self.validate_list(key, value)
        
        # Default to string validation (basic check)
        if len(value) > 1000:
            self.warnings.append(f"{key} value is very long ({len(value)} characters)")
        
        self.passed.append(f"{key} string format is valid")
        return True
    
    def validate_critical_variables(self, env_vars: Dict[str, str]) -> bool:
        """Validate critical environment variables."""
        critical_passed = True
        
        # Check GEMINI_API_KEY
        if 'GEMINI_API_KEY' in env_vars:
            if not self.validate_gemini_api_key(env_vars['GEMINI_API_KEY']):
                critical_passed = False
        else:
            self.errors.append("GEMINI_API_KEY is missing")
            critical_passed = False
        
        # Check MONGODB_URI
        if 'MONGODB_URI' in env_vars:
            if not self.validate_mongodb_uri(env_vars['MONGODB_URI']):
                critical_passed = False
        else:
            self.errors.append("MONGODB_URI is missing")
            critical_passed = False
        
        # Check MONGODB_DB
        if 'MONGODB_DB' in env_vars:
            if not self.validate_mongodb_db(env_vars['MONGODB_DB']):
                critical_passed = False
        else:
            self.errors.append("MONGODB_DB is missing")
            critical_passed = False
        
        return critical_passed
    
    def validate_variable_formats(self, env_vars: Dict[str, str]) -> None:
        """Validate format of all environment variables."""
        # Define validation rules for known variables
        boolean_vars = {
            'DEBUG', 'LOG_TO_FILE', 'ENABLE_METRICS', 'ENABLE_CACHE',
            'RATE_LIMIT_ENABLED', 'ENABLE_COMPRESSION', 'CORS_ENABLED',
            'SCRAPER_RESPECT_ROBOTS', 'ENABLE_CONTENT_CLEANING', 'ENABLE_AI_ANALYSIS',
            'ENABLE_SUMMARIZATION', 'ENABLE_STRUCTURED_EXTRACTION', 'ENABLE_DUPLICATE_DETECTION',
            'DATABASE_ENABLE_TEXT_SEARCH', 'DATABASE_ENABLE_CONTENT_TTL', 'DATABASE_ENABLE_CACHING',
            'DATABASE_ENABLE_COMPRESSION', 'DATABASE_INDEX_BACKGROUND', 'DATABASE_ENABLE_PROFILING',
            'API_ENABLE_REQUEST_LOGGING', 'API_ENABLE_ANALYTICS_TRACKING', 'API_ENABLE_DETAILED_ERRORS',
            'API_ENABLE_PROGRESS_TRACKING', 'API_DEFAULT_PROCESSING_CONFIG', 'API_ENABLE_DATABASE_STORAGE',
            'CACHE_ENABLED', 'CACHE_RESPONSE_ENABLED', 'LOG_REQUEST_BODY', 'LOG_RESPONSE_BODY',
            'METRICS_ENABLED', 'ENABLE_COMPRESSION'
        }
        
        integer_vars = {
            'PORT', 'WORKERS', 'MAX_CONNECTIONS', 'CONNECTION_TIMEOUT',
            'REQUEST_TIMEOUT', 'RATE_LIMIT_REQUESTS', 'RATE_LIMIT_WINDOW',
            'CACHE_TTL', 'MAX_RETRIES', 'RETRY_DELAY', 'MONGODB_MAX_POOL_SIZE',
            'MONGODB_MIN_POOL_SIZE', 'MONGODB_MAX_IDLE_TIME_MS', 'MONGODB_SERVER_SELECTION_TIMEOUT_MS',
            'MONGODB_CONNECT_TIMEOUT_MS', 'GEMINI_MAX_TOKENS', 'GEMINI_MAX_CONTENT_LENGTH',
            'GEMINI_MAX_SIMILARITY_CONTENT_LENGTH', 'AGENT_TIMEOUT_SECONDS', 'PARSER_TIMEOUT_SECONDS',
            'CATEGORIZER_TIMEOUT_SECONDS', 'PROCESSOR_TIMEOUT_SECONDS', 'AGENT_MAX_RETRIES',
            'SCRAPER_CONCURRENCY', 'SCRAPER_REQUEST_TIMEOUT_SECONDS', 'SCRAPER_MAX_RETRIES',
            'SCRAPER_MAX_REDIRECTS', 'SCRAPER_CONTENT_SIZE_LIMIT', 'PROCESSING_TIMEOUT_SECONDS',
            'PROCESSING_MAX_RETRIES', 'PROCESSING_CONCURRENCY', 'PROCESSING_BATCH_SIZE',
            'CONTENT_PROCESSING_TIMEOUT', 'MAX_CONCURRENT_AI_ANALYSES', 'MAX_PROCESSING_MEMORY',
            'MAX_SUMMARY_LENGTH', 'PROCESSING_MAX_SIMILARITY_CONTENT_PAIRS', 'PROCESSING_MAX_SIMILARITY_BATCH_SIZE',
            'DATABASE_QUERY_TIMEOUT_SECONDS', 'DATABASE_MAX_RETRIES', 'DATABASE_BATCH_SIZE',
            'DATABASE_CACHE_TTL_SECONDS', 'DATABASE_MAX_CONTENT_SIZE_MB', 'DATABASE_CONTENT_TTL_DAYS',
            'DATABASE_ANALYTICS_RETENTION_DAYS', 'HEALTH_AGENT_TEST_TIMEOUT', 'HEALTH_PROCESSING_TEST_TIMEOUT',
            'API_REQUEST_TIMEOUT_SECONDS', 'API_MAX_QUERY_LENGTH', 'API_MAX_RESULTS_PER_REQUEST',
            'API_RATE_LIMIT_REQUESTS_PER_MINUTE', 'API_KEY_RATE_LIMIT_PER_MINUTE', 'CACHE_TTL_SECONDS',
            'CACHE_MAX_SIZE', 'LOG_MAX_BYTES', 'LOG_BACKUP_COUNT', 'HEALTH_CHECK_INTERVAL_SECONDS',
            'MAX_CONNECTIONS'
        }
        
        float_vars = {
            'RATE_LIMIT_BURST', 'CONNECTION_POOL_SIZE', 'TIMEOUT_MULTIPLIER',
            'GEMINI_TEMPERATURE', 'AGENT_CONFIDENCE_THRESHOLD', 'SCRAPER_DELAY_SECONDS',
            'SIMILARITY_THRESHOLD', 'MIN_CONTENT_QUALITY_SCORE'
        }
        
        list_vars = {
            'ALLOWED_ORIGINS', 'ALLOWED_HOSTS', 'TRUSTED_PROXIES', 'API_PUBLIC_ENDPOINTS'
        }
        
        # Additional validation based on patterns and comments from env.example
        for key, value in env_vars.items():
            if key in boolean_vars:
                self.validate_boolean(key, value)
            elif key in integer_vars:
                self.validate_integer(key, value)
            elif key in float_vars:
                self.validate_float(key, value)
            elif key in list_vars:
                self.validate_list(key, value)
            else:
                # Infer type from common patterns
                self.validate_by_pattern(key, value)
    
    def compare_with_example(self, env_vars: Dict[str, str]) -> None:
        """Compare .env with .env.example to find missing or extra variables."""
        example_vars = self.parse_env_file(self.env_example_file)
        
        # Find missing variables
        missing_vars = set(example_vars.keys()) - set(env_vars.keys())
        for var in missing_vars:
            self.warnings.append(f"Missing optional variable: {var}")
        
        # Find extra variables (potential typos)
        extra_vars = set(env_vars.keys()) - set(example_vars.keys())
        for var in extra_vars:
            self.warnings.append(f"Extra variable not in .env.example: {var}")
        
        if missing_vars:
            self.print_status(f"Found {len(missing_vars)} missing optional variables", "warning")
        if extra_vars:
            self.print_status(f"Found {len(extra_vars)} extra variables", "warning")
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print(f"{Colors.BOLD}{Colors.CYAN}🔍 Environment Validation Report{Colors.END}")
        print(f"{Colors.CYAN}{'='*50}{Colors.END}")
        
        # Check file existence
        if not self.check_file_existence():
            return False
        
        # Parse environment files
        env_vars = self.parse_env_file(self.env_file)
        required_vars = self.extract_required_vars_from_example()
        
        if not env_vars:
            self.errors.append("No environment variables found in .env file")
            return False
        
        self.print_status(f"Found {len(env_vars)} environment variables", "success")
        
        # Check for missing required variables
        print(f"\n{Colors.BOLD}Required Variables Check:{Colors.END}")
        for var_name, default_value in required_vars.items():
            if var_name not in env_vars:
                self.errors.append(f"Missing required variable: {var_name}")
                self.print_status(f"Missing required variable: {var_name}", "error")
                if default_value:
                    self.print_status(f"  Default value: {default_value}", "info")
            else:
                self.print_status(f"✓ {var_name} is present", "success")
        
        # Validate critical variables
        print(f"\n{Colors.BOLD}Critical Variables:{Colors.END}")
        critical_passed = self.validate_critical_variables(env_vars)
        
        # Validate variable formats
        print(f"\n{Colors.BOLD}Format Validation:{Colors.END}")
        self.validate_variable_formats(env_vars)
        
        # Compare with example
        print(f"\n{Colors.BOLD}Configuration Completeness:{Colors.END}")
        self.compare_with_example(env_vars)
        
        # Print summary
        self.print_summary()
        
        return len(self.errors) == 0
    
    def print_summary(self) -> None:
        """Print validation summary."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Validation Summary{Colors.END}")
        print(f"{Colors.CYAN}{'='*50}{Colors.END}")
        
        total_checks = len(self.passed) + len(self.errors) + len(self.warnings)
        
        if self.passed:
            print(f"{Colors.GREEN}✅ Passed: {len(self.passed)}{Colors.END}")
            for item in self.passed:
                print(f"   {Colors.GREEN}✓{Colors.END} {item}")
        
        if self.warnings:
            print(f"\n{Colors.YELLOW}⚠️  Warnings: {len(self.warnings)}{Colors.END}")
            for item in self.warnings:
                print(f"   {Colors.YELLOW}⚠{Colors.END} {item}")
        
        if self.errors:
            print(f"\n{Colors.RED}❌ Errors: {len(self.errors)}{Colors.END}")
            for item in self.errors:
                print(f"   {Colors.RED}✗{Colors.END} {item}")
        
        print(f"\n{Colors.BOLD}Total checks: {total_checks}{Colors.END}")
        
        if len(self.errors) == 0:
            if len(self.warnings) == 0:
                print(f"{Colors.GREEN}{Colors.BOLD}🎉 All validations passed!{Colors.END}")
            else:
                print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Validations passed with warnings{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ Validation failed{Colors.END}")
            print(f"\n{Colors.YELLOW}💡 Recommendations:{Colors.END}")
            print("   1. Fix all errors before running the application")
            print("   2. Review warnings and address if needed")
            print("   3. Run 'python scripts/fix_env.py' for interactive fixes")
            print("   4. Check docs/ENVIRONMENT_SETUP.md for detailed setup guide")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument("--project-root", type=str, default=".", 
                       help="Project root directory (default: current directory)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    
    if not project_root.exists():
        print(f"{Colors.RED}❌ Project root not found: {project_root}{Colors.END}")
        sys.exit(1)
    
    validator = EnvValidator(project_root)
    
    try:
        success = validator.validate_all()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Validation interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Unexpected error during validation: {e}{Colors.END}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
