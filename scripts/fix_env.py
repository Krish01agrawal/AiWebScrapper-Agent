#!/usr/bin/env python3
"""
Interactive environment configuration fixer for AI Web Scraper project.

This script helps fix common environment configuration issues by providing
interactive prompts, validation, and automatic fixes for missing or
incorrect environment variables.

Usage:
    python scripts/fix_env.py
    python scripts/fix_env.py --auto
    python scripts/fix_env.py --interactive
    python scripts/fix_env.py --backup-only
    python scripts/fix_env.py --restore backup.env

Exit codes:
    0 - Environment fixed successfully
    1 - Cannot fix or user cancelled
"""

import os
import sys
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import argparse
import re

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from scripts.validate_env import EnvValidator
    from scripts.test_connections import ConnectionTester
    import asyncio
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the project root and dependencies are installed")
    sys.exit(1)


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


class EnvFixer:
    """Interactive environment configuration fixer."""
    
    def __init__(self, project_root: Path, auto_mode: bool = False, 
                 backup_only: bool = False, restore_file: Optional[str] = None):
        self.project_root = project_root
        self.auto_mode = auto_mode
        self.backup_only = backup_only
        self.restore_file = restore_file
        self.env_file = project_root / '.env'
        self.env_example_file = project_root / '.env.example'
        self.backup_file = None
        self.changes_made = []
        
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
    
    def print_header(self):
        """Print script header."""
        print(f"{Colors.BOLD}{Colors.CYAN}🔧 Environment Configuration Fixer{Colors.END}")
        print(f"{Colors.CYAN}{'='*50}{Colors.END}")
        print(f"Project: {self.project_root.name}")
        print(f"Mode: {'Auto' if self.auto_mode else 'Interactive'}")
        print()
    
    def create_backup(self) -> bool:
        """Create backup of .env file."""
        if not self.env_file.exists():
            return True
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.backup_file = self.project_root / f".env.backup.{timestamp}"
        
        try:
            shutil.copy2(self.env_file, self.backup_file)
            self.print_status(f"Backup created: {self.backup_file.name}", "success")
            return True
        except Exception as e:
            self.print_status(f"Failed to create backup: {e}", "error")
            return False
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore .env from backup file."""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            self.print_status(f"Backup file not found: {backup_path}", "error")
            return False
        
        try:
            shutil.copy2(backup_file, self.env_file)
            self.print_status(f"Restored from backup: {backup_path}", "success")
            return True
        except Exception as e:
            self.print_status(f"Failed to restore from backup: {e}", "error")
            return False
    
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
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
        
        return env_vars
    
    def write_env_file(self, env_vars: Dict[str, str]) -> bool:
        """Write environment variables to .env file."""
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write("# AI Web Scraper Environment Configuration\n")
                f.write("# Generated by fix_env.py\n")
                f.write(f"# Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Write variables in logical groups
                groups = {
                    "API Configuration": ["GEMINI_API_KEY"],
                    "Database Configuration": ["MONGODB_URI", "MONGODB_DB"],
                    "Server Configuration": ["PORT", "WORKERS", "DEBUG", "LOG_LEVEL"],
                    "Performance Configuration": ["CONNECTION_TIMEOUT", "REQUEST_TIMEOUT", "RATE_LIMIT_REQUESTS", "CACHE_TTL"],
                    "Security Configuration": ["CORS_ENABLED", "ALLOWED_ORIGINS", "ENABLE_METRICS"],
                    "Other Configuration": []
                }
                
                # Categorize variables
                categorized = {group: [] for group in groups}
                uncategorized = []
                
                for key, value in env_vars.items():
                    categorized_flag = False
                    for group, vars_list in groups.items():
                        if key in vars_list:
                            categorized[group].append((key, value))
                            categorized_flag = True
                            break
                    if not categorized_flag:
                        uncategorized.append((key, value))
                
                categorized["Other Configuration"] = uncategorized
                
                # Write groups
                for group_name, vars_list in categorized.items():
                    if vars_list:
                        f.write(f"\n# {group_name}\n")
                        for key, value in vars_list:
                            f.write(f"{key}={value}\n")
            
            self.print_status(f"Environment file updated: {self.env_file}", "success")
            return True
            
        except Exception as e:
            self.print_status(f"Failed to write .env file: {e}", "error")
            return False
    
    def get_user_input(self, prompt: str, default: Optional[str] = None, 
                      validator: Optional[callable] = None) -> str:
        """Get user input with validation."""
        if self.auto_mode and default:
            return default
        
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if validator:
                try:
                    if validator(user_input):
                        return user_input
                    else:
                        print(f"{Colors.RED}Invalid input. Please try again.{Colors.END}")
                        continue
                except Exception as e:
                    print(f"{Colors.RED}Validation error: {e}{Colors.END}")
                    continue
            else:
                return user_input
    
    def validate_gemini_api_key(self, api_key: str) -> bool:
        """Validate Gemini API key format."""
        if not api_key:
            return False
        
        if api_key in ["your_api_key_here", "gemini_api_key", "AIzaSy"]:
            return False
        
        if len(api_key) < 20:
            return False
        
        return True
    
    def validate_mongodb_uri(self, uri: str) -> bool:
        """Validate MongoDB URI format."""
        if not uri:
            return False
        
        return uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")
    
    def validate_mongodb_db(self, db_name: str) -> bool:
        """Validate MongoDB database name."""
        if not db_name:
            return False
        
        return re.match(r'^[a-zA-Z0-9_-]+$', db_name) is not None
    
    def validate_port(self, port: str) -> bool:
        """Validate port number."""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except ValueError:
            return False
    
    def validate_boolean(self, value: str) -> bool:
        """Validate boolean value."""
        return value.lower() in ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n']
    
    def normalize_boolean(self, value: str) -> str:
        """Normalize boolean value to 'true' or 'false'."""
        if value.lower() in ['true', '1', 'yes', 'y']:
            return 'true'
        else:
            return 'false'
    
    def fix_missing_env_file(self) -> bool:
        """Fix missing .env file."""
        if self.env_file.exists():
            return True
        
        self.print_status(".env file not found", "warning")
        
        if not self.env_example_file.exists():
            self.print_status(".env.example not found", "error")
            return False
        
        if self.auto_mode:
            shutil.copy2(self.env_example_file, self.env_file)
            self.print_status("Created .env from .env.example", "success")
            self.changes_made.append("Created .env file")
            return True
        
        response = self.get_user_input("Create .env from .env.example? (yes/no)", "yes")
        if response.lower() in ['y', 'yes']:
            shutil.copy2(self.env_example_file, self.env_file)
            self.print_status("Created .env from .env.example", "success")
            self.changes_made.append("Created .env file")
            return True
        
        return False
    
    def fix_gemini_api_key(self, env_vars: Dict[str, str]) -> bool:
        """Fix Gemini API key configuration."""
        current_key = env_vars.get('GEMINI_API_KEY', '')
        
        if self.validate_gemini_api_key(current_key):
            self.print_status("GEMINI_API_KEY is valid", "success")
            return True
        
        self.print_status("GEMINI_API_KEY needs configuration", "warning")
        print(f"{Colors.CYAN}Get your API key from: https://makersuite.google.com/app/apikey{Colors.END}")
        
        api_key = self.get_user_input(
            "Enter your Gemini API key",
            validator=self.validate_gemini_api_key
        )
        
        if api_key:
            env_vars['GEMINI_API_KEY'] = api_key
            self.changes_made.append("Configured GEMINI_API_KEY")
            self.print_status("GEMINI_API_KEY configured", "success")
            return True
        
        return False
    
    def fix_mongodb_uri(self, env_vars: Dict[str, str]) -> bool:
        """Fix MongoDB URI configuration."""
        current_uri = env_vars.get('MONGODB_URI', '')
        
        if self.validate_mongodb_uri(current_uri):
            self.print_status("MONGODB_URI is valid", "success")
            return True
        
        self.print_status("MONGODB_URI needs configuration", "warning")
        print(f"{Colors.CYAN}Common MongoDB URIs:{Colors.END}")
        print("  Local: mongodb://localhost:27017")
        print("  Atlas: mongodb+srv://username:password@cluster.mongodb.net/")
        print("  Docker: mongodb://mongodb:27017")
        
        mongodb_uri = self.get_user_input(
            "Enter MongoDB URI",
            default="mongodb://localhost:27017",
            validator=self.validate_mongodb_uri
        )
        
        if mongodb_uri:
            env_vars['MONGODB_URI'] = mongodb_uri
            self.changes_made.append("Configured MONGODB_URI")
            self.print_status("MONGODB_URI configured", "success")
            return True
        
        return False
    
    def fix_mongodb_db(self, env_vars: Dict[str, str]) -> bool:
        """Fix MongoDB database name configuration."""
        current_db = env_vars.get('MONGODB_DB', '')
        
        if self.validate_mongodb_db(current_db):
            self.print_status("MONGODB_DB is valid", "success")
            return True
        
        self.print_status("MONGODB_DB needs configuration", "warning")
        
        db_name = self.get_user_input(
            "Enter MongoDB database name",
            default="traycer_try",
            validator=self.validate_mongodb_db
        )
        
        if db_name:
            env_vars['MONGODB_DB'] = db_name
            self.changes_made.append("Configured MONGODB_DB")
            self.print_status("MONGODB_DB configured", "success")
            return True
        
        return False
    
    def fix_port_configuration(self, env_vars: Dict[str, str]) -> bool:
        """Fix port configuration."""
        current_port = env_vars.get('PORT', '8000')
        
        if self.validate_port(current_port):
            self.print_status("PORT is valid", "success")
            return True
        
        self.print_status("PORT needs configuration", "warning")
        
        port = self.get_user_input(
            "Enter server port",
            default="8000",
            validator=self.validate_port
        )
        
        if port:
            env_vars['PORT'] = port
            self.changes_made.append("Configured PORT")
            self.print_status("PORT configured", "success")
            return True
        
        return False
    
    def fix_debug_configuration(self, env_vars: Dict[str, str]) -> bool:
        """Fix debug configuration."""
        current_debug = env_vars.get('DEBUG', 'false')
        
        if self.validate_boolean(current_debug):
            self.print_status("DEBUG is valid", "success")
            return True
        
        self.print_status("DEBUG needs configuration", "warning")
        
        debug = self.get_user_input(
            "Enable debug mode? (yes/no)",
            default="yes" if not self.auto_mode else "false",
            validator=self.validate_boolean
        )
        
        if debug:
            normalized_debug = self.normalize_boolean(debug)
            env_vars['DEBUG'] = normalized_debug
            self.changes_made.append("Configured DEBUG")
            self.print_status("DEBUG configured", "success")
            return True
        
        return False
    
    def fix_common_issues(self, env_vars: Dict[str, str]) -> bool:
        """Fix common configuration issues."""
        issues_fixed = 0
        
        # Fix boolean values
        boolean_vars = ['CORS_ENABLED', 'ENABLE_METRICS', 'LOG_TO_FILE']
        for var in boolean_vars:
            if var in env_vars:
                value = env_vars[var]
                if not self.validate_boolean(value):
                    normalized = self.normalize_boolean(value)
                    env_vars[var] = normalized
                    self.changes_made.append(f"Fixed {var} boolean value")
                    issues_fixed += 1
        
        # Fix numeric values
        numeric_vars = ['WORKERS', 'CONNECTION_TIMEOUT', 'REQUEST_TIMEOUT']
        for var in numeric_vars:
            if var in env_vars:
                value = env_vars[var]
                try:
                    int(value)
                except ValueError:
                    if var == 'WORKERS':
                        env_vars[var] = '1'
                    elif 'TIMEOUT' in var:
                        env_vars[var] = '30'
                    self.changes_made.append(f"Fixed {var} numeric value")
                    issues_fixed += 1
        
        if issues_fixed > 0:
            self.print_status(f"Fixed {issues_fixed} common issues", "success")
        
        return True
    
    def run_validation_after_fix(self) -> bool:
        """Run validation after fixes."""
        self.print_status("Running validation after fixes...", "info")
        
        try:
            validator = EnvValidator(self.project_root)
            success = validator.validate_all()
            
            if success:
                self.print_status("Validation passed after fixes", "success")
                return True
            else:
                self.print_status("Validation still has issues", "warning")
                if validator.errors:
                    for error in validator.errors:
                        self.print_status(f"  {error}", "error")
                return False
                
        except Exception as e:
            self.print_status(f"Validation failed: {e}", "error")
            return False
    
    async def test_connections_after_fix(self) -> bool:
        """Test connections after fixes."""
        self.print_status("Testing connections after fixes...", "info")
        
        try:
            tester = ConnectionTester(timeout=10, verbose=False)
            results = await tester.test_all_connections()
            
            success_count = sum(1 for result in results.values() if result["status"] == "success")
            total_count = len(results)
            
            if success_count == total_count:
                self.print_status("All connections successful", "success")
                return True
            elif success_count > 0:
                self.print_status("Partial connectivity", "warning")
                return True
            else:
                self.print_status("All connections failed", "error")
                return False
                
        except Exception as e:
            self.print_status(f"Connection test failed: {e}", "error")
            return False
    
    def show_changes_summary(self):
        """Show summary of changes made."""
        if not self.changes_made:
            self.print_status("No changes made", "info")
            return
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Changes Made{Colors.END}")
        print(f"{Colors.CYAN}{'='*30}{Colors.END}")
        
        for i, change in enumerate(self.changes_made, 1):
            print(f"{Colors.GREEN}{i}. {change}{Colors.END}")
        
        if self.backup_file:
            print(f"\n{Colors.YELLOW}💾 Backup created: {self.backup_file.name}{Colors.END}")
            print(f"   To restore: python scripts/fix_env.py --restore {self.backup_file.name}")
    
    def run_guided_setup(self) -> bool:
        """Run guided setup for first-time users."""
        self.print_status("Starting guided environment setup...", "info")
        print(f"{Colors.CYAN}This will walk you through configuring your environment step by step.{Colors.END}\n")
        
        # Create backup
        if not self.create_backup():
            return False
        
        # Fix missing .env file
        if not self.fix_missing_env_file():
            return False
        
        # Parse current environment
        env_vars = self.parse_env_file(self.env_file)
        
        # Fix critical variables
        critical_fixes = [
            ("GEMINI_API_KEY", self.fix_gemini_api_key),
            ("MONGODB_URI", self.fix_mongodb_uri),
            ("MONGODB_DB", self.fix_mongodb_db),
        ]
        
        for var_name, fix_func in critical_fixes:
            if not fix_func(env_vars):
                self.print_status(f"Failed to configure {var_name}", "error")
                return False
        
        # Fix optional variables
        optional_fixes = [
            ("PORT", self.fix_port_configuration),
            ("DEBUG", self.fix_debug_configuration),
        ]
        
        for var_name, fix_func in optional_fixes:
            fix_func(env_vars)
        
        # Fix common issues
        self.fix_common_issues(env_vars)
        
        # Write updated environment file
        if not self.write_env_file(env_vars):
            return False
        
        # Show changes summary
        self.show_changes_summary()
        
        # Run validation
        if not self.run_validation_after_fix():
            self.print_status("Environment setup completed with warnings", "warning")
            return True
        
        # Test connections
        try:
            asyncio.run(self.test_connections_after_fix())
        except Exception as e:
            self.print_status(f"Connection test failed: {e}", "warning")
        
        self.print_status("Guided setup completed successfully", "success")
        return True
    
    def run_auto_fix(self) -> bool:
        """Run automatic fixes using defaults."""
        self.print_status("Running automatic fixes...", "info")
        
        # Create backup
        if not self.create_backup():
            return False
        
        # Fix missing .env file
        if not self.fix_missing_env_file():
            return False
        
        # Parse current environment
        env_vars = self.parse_env_file(self.env_file)
        
        # Apply default values for missing critical variables
        defaults = {
            'GEMINI_API_KEY': 'your_api_key_here',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DB': 'traycer_try',
            'PORT': '8000',
            'DEBUG': 'true',
            'WORKERS': '1',
            'CONNECTION_TIMEOUT': '30',
            'REQUEST_TIMEOUT': '60',
            'CORS_ENABLED': 'true',
            'ENABLE_METRICS': 'true',
        }
        
        for key, default_value in defaults.items():
            if key not in env_vars or not env_vars[key]:
                env_vars[key] = default_value
                self.changes_made.append(f"Set {key} to default value")
        
        # Write updated environment file
        if not self.write_env_file(env_vars):
            return False
        
        # Show changes summary
        self.show_changes_summary()
        
        self.print_status("Automatic fixes completed", "success")
        self.print_status("Please edit .env file with your actual values", "warning")
        return True
    
    def run_fix(self) -> bool:
        """Main fix function."""
        self.print_header()
        
        # Handle restore operation
        if self.restore_file:
            return self.restore_from_backup(self.restore_file)
        
        # Handle backup-only operation
        if self.backup_only:
            return self.create_backup()
        
        # Run appropriate fix mode
        if self.auto_mode:
            return self.run_auto_fix()
        else:
            return self.run_guided_setup()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fix environment configuration issues")
    parser.add_argument("--auto", action="store_true", 
                       help="Run in auto mode (non-interactive)")
    parser.add_argument("--interactive", action="store_true", 
                       help="Run in interactive mode (default)")
    parser.add_argument("--backup-only", action="store_true", 
                       help="Create backup only")
    parser.add_argument("--restore", type=str, 
                       help="Restore from backup file")
    parser.add_argument("--project-root", type=str, default=".", 
                       help="Project root directory")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    
    if not project_root.exists():
        print(f"{Colors.RED}❌ Project root not found: {project_root}{Colors.END}")
        sys.exit(1)
    
    fixer = EnvFixer(
        project_root=project_root,
        auto_mode=args.auto,
        backup_only=args.backup_only,
        restore_file=args.restore
    )
    
    try:
        success = fixer.run_fix()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Fix interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Unexpected error during fix: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
