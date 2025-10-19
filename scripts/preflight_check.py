#!/usr/bin/env python3
"""
Pre-flight check orchestrator for AI Web Scraper project.

This script runs comprehensive validation checks before starting the application.
It orchestrates environment validation, dependency checks, connection tests,
configuration validation, and file system checks.

Usage:
    python scripts/preflight_check.py
    python scripts/preflight_check.py --skip-connections
    python scripts/preflight_check.py --ci --json-output
    python scripts/preflight_check.py --verbose --fix-permissions

Exit codes:
    0 - All checks passed, ready to start
    1 - Critical failures, cannot start
    2 - Warnings present, can start but may have issues
"""

import asyncio
import json
import os
import sys
import time
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import argparse
import subprocess

# Try to import psutil, fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file explicitly before importing settings
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')
except ImportError:
    # python-dotenv not installed, continue without explicit loading
    pass

try:
    from scripts.validate_env import EnvValidator
    from scripts.test_connections import ConnectionTester
    from app.core.config import get_settings
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


class PreflightChecker:
    """Pre-flight check orchestrator."""
    
    def __init__(self, project_root: Path, skip_connections: bool = False, 
                 skip_dependencies: bool = False, verbose: bool = False,
                 ci_mode: bool = False, fix_permissions: bool = False):
        self.project_root = project_root
        self.skip_connections = skip_connections
        self.skip_dependencies = skip_dependencies
        self.verbose = verbose
        self.ci_mode = ci_mode
        self.fix_permissions = fix_permissions
        
        self.results = {
            "timestamp": time.time(),
            "phases": {},
            "summary": {
                "overall_status": "unknown",
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            },
            "system_info": self._get_system_info(),
            "recommendations": []
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            base_info = {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
            }
            
            if PSUTIL_AVAILABLE:
                base_info.update({
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                    "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
                })
            else:
                base_info["psutil_unavailable"] = "psutil not installed - detailed system info unavailable"
            
            return base_info
        except Exception:
            return {"error": "Could not gather system information"}
    
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
    
    def print_phase_header(self, phase_name: str, phase_number: int):
        """Print phase header."""
        print(f"\n{Colors.BOLD}{Colors.PURPLE}Phase {phase_number}: {phase_name}{Colors.END}")
        print(f"{Colors.PURPLE}{'='*60}{Colors.END}")
    
    def phase_1_environment_validation(self) -> Dict[str, Any]:
        """Phase 1: Environment validation."""
        self.print_phase_header("Environment Validation", 1)
        
        phase_result = {
            "name": "Environment Validation",
            "status": "unknown",
            "checks": [],
            "errors": [],
            "warnings": [],
            "passed": 0,
            "failed": 0
        }
        
        try:
            validator = EnvValidator(self.project_root)
            success = validator.validate_all()
            
            phase_result["status"] = "success" if success else "failed"
            phase_result["errors"] = validator.errors
            phase_result["warnings"] = validator.warnings
            phase_result["passed"] = len(validator.passed)
            phase_result["failed"] = len(validator.errors)
            
            # Check for critical failures
            critical_vars = ["GEMINI_API_KEY", "MONGODB_URI", "MONGODB_DB"]
            critical_failures = [error for error in validator.errors 
                               if any(var in error for var in critical_vars)]
            
            if critical_failures:
                phase_result["status"] = "failed"
                self.print_status("Critical environment variables missing", "error")
                for error in critical_failures:
                    self.print_status(f"  {error}", "error")
            elif validator.errors:
                phase_result["status"] = "warning"
                self.print_status("Environment validation completed with errors", "warning")
            else:
                self.print_status("Environment validation passed", "success")
            
        except Exception as e:
            phase_result["status"] = "failed"
            phase_result["errors"].append(f"Validation error: {str(e)}")
            self.print_status(f"Environment validation failed: {e}", "error")
            if self.verbose:
                import traceback
                traceback.print_exc()
        
        return phase_result
    
    def phase_2_dependency_check(self) -> Dict[str, Any]:
        """Phase 2: Dependency check."""
        self.print_phase_header("Dependency Check", 2)
        
        phase_result = {
            "name": "Dependency Check",
            "status": "unknown",
            "checks": [],
            "errors": [],
            "warnings": [],
            "passed": 0,
            "failed": 0
        }
        
        try:
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                phase_result["errors"].append("requirements.txt not found")
                phase_result["status"] = "failed"
                self.print_status("requirements.txt not found", "error")
                return phase_result
            
            # Read requirements
            with open(requirements_file, 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            self.print_status(f"Checking {len(requirements)} required packages", "info")
            
            missing_packages = []
            outdated_packages = []
            
            # Import version checking modules
            try:
                from packaging import version, specifiers
                from packaging.requirements import Requirement
            except ImportError:
                self.print_status("packaging module not available - version checking disabled", "warning")
                packaging_available = False
            else:
                packaging_available = True
            
            for requirement in requirements:
                package_name = requirement.split('==')[0].split('>=')[0].split('<=')[0]
                
                try:
                    # Try to import the package
                    if package_name == "python-dotenv":
                        import dotenv
                        installed_version = getattr(dotenv, '__version__', 'unknown')
                    elif package_name == "motor":
                        import motor
                        installed_version = getattr(motor, '__version__', 'unknown')
                    elif package_name == "google-generativeai":
                        import google.generativeai
                        installed_version = getattr(google.generativeai, '__version__', 'unknown')
                    elif package_name == "pydantic-settings":
                        import pydantic_settings
                        installed_version = getattr(pydantic_settings, '__version__', 'unknown')
                    elif package_name == "fastapi":
                        import fastapi
                        installed_version = getattr(fastapi, '__version__', 'unknown')
                    elif package_name == "uvicorn":
                        import uvicorn
                        installed_version = getattr(uvicorn, '__version__', 'unknown')
                    else:
                        # Generic import attempt
                        module = __import__(package_name.replace('-', '_'))
                        installed_version = getattr(module, '__version__', 'unknown')
                    
                    # Check version compatibility if packaging is available
                    if packaging_available and installed_version != 'unknown':
                        try:
                            req = Requirement(requirement)
                            if not req.specifier.contains(installed_version):
                                outdated_packages.append({
                                    'name': package_name,
                                    'installed': installed_version,
                                    'required': str(req.specifier),
                                    'requirement': requirement
                                })
                                self.print_status(f"⚠ {package_name} version mismatch: installed {installed_version}, required {req.specifier}", "warning")
                                phase_result["warnings"].append(f"{package_name}: version {installed_version} doesn't match requirement {req.specifier}")
                            else:
                                self.print_status(f"✓ {package_name} {installed_version} (compatible)", "success")
                        except Exception as e:
                            self.print_status(f"✓ {package_name} {installed_version} (version check failed: {e})", "success")
                    else:
                        self.print_status(f"✓ {package_name} {installed_version}", "success")
                    
                    phase_result["passed"] += 1
                        
                except ImportError:
                    missing_packages.append(package_name)
                    phase_result["failed"] += 1
                    self.print_status(f"✗ {package_name} (not installed)", "error")
                except Exception as e:
                    phase_result["warnings"].append(f"{package_name}: {str(e)}")
                    self.print_status(f"⚠ {package_name} (import warning)", "warning")
            
            if missing_packages:
                phase_result["errors"].extend([f"Missing package: {pkg}" for pkg in missing_packages])
                phase_result["status"] = "failed"
                self.print_status(f"Missing {len(missing_packages)} required packages", "error")
                self.results["recommendations"].append("Run 'pip install -r requirements.txt' to install missing packages")
            elif outdated_packages:
                phase_result["status"] = "warning"
                self.print_status(f"Found {len(outdated_packages)} packages with version mismatches", "warning")
                self.results["recommendations"].append("Run 'pip install -r requirements.txt --upgrade' to update packages")
            else:
                phase_result["status"] = "success"
                self.print_status("All required packages are installed with compatible versions", "success")
            
        except Exception as e:
            phase_result["status"] = "failed"
            phase_result["errors"].append(f"Dependency check error: {str(e)}")
            self.print_status(f"Dependency check failed: {e}", "error")
            if self.verbose:
                import traceback
                traceback.print_exc()
        
        return phase_result
    
    async def phase_3_connection_tests(self) -> Dict[str, Any]:
        """Phase 3: Connection tests."""
        self.print_phase_header("Connection Tests", 3)
        
        phase_result = {
            "name": "Connection Tests",
            "status": "unknown",
            "checks": [],
            "errors": [],
            "warnings": [],
            "passed": 0,
            "failed": 0
        }
        
        if self.skip_connections:
            self.print_status("Connection tests skipped", "info")
            phase_result["status"] = "skipped"
            return phase_result
        
        try:
            tester = ConnectionTester(timeout=10, verbose=self.verbose)
            connection_results = await tester.test_all_connections()
            
            for service, result in connection_results.items():
                if result["status"] == "success":
                    phase_result["passed"] += 1
                    self.print_status(f"{service} connection successful", "success")
                else:
                    phase_result["failed"] += 1
                    phase_result["errors"].append(f"{service}: {result.get('error', 'Connection failed')}")
                    self.print_status(f"{service} connection failed", "error")
            
            if phase_result["failed"] == 0:
                phase_result["status"] = "success"
                self.print_status("All connections successful", "success")
            elif phase_result["passed"] > 0:
                phase_result["status"] = "warning"
                self.print_status("Partial connectivity", "warning")
            else:
                phase_result["status"] = "failed"
                self.print_status("All connections failed", "error")
                self.results["recommendations"].append("Check network connectivity and API credentials")
            
        except Exception as e:
            phase_result["status"] = "failed"
            phase_result["errors"].append(f"Connection test error: {str(e)}")
            self.print_status(f"Connection tests failed: {e}", "error")
            if self.verbose:
                import traceback
                traceback.print_exc()
        
        return phase_result
    
    def phase_4_configuration_validation(self) -> Dict[str, Any]:
        """Phase 4: Configuration validation."""
        self.print_phase_header("Configuration Validation", 4)
        
        phase_result = {
            "name": "Configuration Validation",
            "status": "unknown",
            "checks": [],
            "errors": [],
            "warnings": [],
            "passed": 0,
            "failed": 0
        }
        
        try:
            settings = get_settings()
            
            # Validate configuration ranges with safe field access
            config_fields = [
                ("workers", 1, 32, "Workers must be between 1 and 32"),
                ("api_request_timeout_seconds", 1, 600, "Request timeout must be between 1 and 600 seconds"),
                ("mongodb_connect_timeout_ms", 1000, 60000, "MongoDB connect timeout must be between 1000 and 60000 milliseconds"),
            ]
            
            for field_name, min_val, max_val, error_msg in config_fields:
                if hasattr(settings, field_name):
                    value = getattr(settings, field_name)
                    if min_val <= value <= max_val:
                        phase_result["passed"] += 1
                        self.print_status(f"{field_name}: {value} (valid)", "success")
                    else:
                        phase_result["failed"] += 1
                        phase_result["errors"].append(f"{field_name}: {error_msg}")
                        self.print_status(f"{field_name}: {value} (invalid)", "error")
                else:
                    if self.verbose:
                        self.print_status(f"{field_name} not defined in Settings; skipping validation", "warning")
                    phase_result["warnings"].append(f"{field_name} not defined in Settings; skipping validation")
            
            # Check for configuration conflicts
            if settings.debug and settings.environment == "production":
                phase_result["warnings"].append("DEBUG=True in production environment")
                self.print_status("DEBUG enabled in production", "warning")
            
            # Check if port validation is needed (only if port field exists)
            if hasattr(settings, 'port') and settings.port == 80 and not settings.debug:
                phase_result["warnings"].append("Using port 80 without DEBUG mode")
                self.print_status("Port 80 without DEBUG mode", "warning")
            
            if phase_result["failed"] == 0:
                phase_result["status"] = "success"
                self.print_status("Configuration validation passed", "success")
            else:
                phase_result["status"] = "failed"
                self.print_status("Configuration validation failed", "error")
            
        except Exception as e:
            phase_result["status"] = "failed"
            phase_result["errors"].append(f"Configuration validation error: {str(e)}")
            self.print_status(f"Configuration validation failed: {e}", "error")
            if self.verbose:
                import traceback
                traceback.print_exc()
        
        return phase_result
    
    def phase_5_file_system_check(self) -> Dict[str, Any]:
        """Phase 5: File system check."""
        self.print_phase_header("File System Check", 5)
        
        phase_result = {
            "name": "File System Check",
            "status": "unknown",
            "checks": [],
            "errors": [],
            "warnings": [],
            "passed": 0,
            "failed": 0
        }
        
        try:
            # Check required directories
            required_dirs = [
                "app",
                "tests", 
                "scripts",
                "app/api",
                "app/core",
                "app/database",
                "app/processing",
                "app/scraper",
                "app/agents",
                "app/services",
                "app/utils"
            ]
            
            for dir_name in required_dirs:
                dir_path = self.project_root / dir_name
                if dir_path.exists() and dir_path.is_dir():
                    phase_result["passed"] += 1
                    self.print_status(f"✓ {dir_name}/", "success")
                else:
                    phase_result["failed"] += 1
                    phase_result["errors"].append(f"Missing directory: {dir_name}")
                    self.print_status(f"✗ {dir_name}/ (missing)", "error")
            
            # Check write permissions for log directory
            if hasattr(get_settings(), 'log_file') and get_settings().log_file:
                log_dir = Path(get_settings().log_file).parent
                if log_dir.exists():
                    if os.access(log_dir, os.W_OK):
                        phase_result["passed"] += 1
                        self.print_status("Log directory writable", "success")
                    else:
                        phase_result["warnings"].append("Log directory not writable")
                        self.print_status("Log directory not writable", "warning")
                        
                        if self.fix_permissions:
                            try:
                                os.chmod(log_dir, 0o755)
                                self.print_status("Fixed log directory permissions", "success")
                            except Exception as e:
                                self.print_status(f"Could not fix permissions: {e}", "error")
            
            # Check Python files are readable
            python_files = list(self.project_root.glob("**/*.py"))
            readable_count = 0
            for py_file in python_files[:10]:  # Check first 10 files
                if os.access(py_file, os.R_OK):
                    readable_count += 1
            
            if readable_count == min(10, len(python_files)):
                phase_result["passed"] += 1
                self.print_status("Python files readable", "success")
            else:
                phase_result["warnings"].append("Some Python files not readable")
                self.print_status("Some Python files not readable", "warning")
            
            if phase_result["failed"] == 0:
                phase_result["status"] = "success"
                self.print_status("File system check passed", "success")
            else:
                phase_result["status"] = "failed"
                self.print_status("File system check failed", "error")
            
        except Exception as e:
            phase_result["status"] = "failed"
            phase_result["errors"].append(f"File system check error: {str(e)}")
            self.print_status(f"File system check failed: {e}", "error")
            if self.verbose:
                import traceback
                traceback.print_exc()
        
        return phase_result
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all pre-flight checks."""
        print(f"{Colors.BOLD}{Colors.CYAN}🚀 Pre-flight Check Report{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"Project: {self.project_root.name}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"System: {platform.system()} {platform.release()}")
        
        start_time = time.time()
        
        # Run phases
        phases = [
            self.phase_1_environment_validation(),
        ]
        
        # Add dependency check only if not skipped
        if not self.skip_dependencies:
            phases.append(self.phase_2_dependency_check())
        else:
            # Add skipped phase result
            phases.append({
                "name": "Dependency Check",
                "status": "skipped",
                "checks": [],
                "errors": [],
                "warnings": [],
                "passed": 0,
                "failed": 0
            })
        
        phases.extend([
            await self.phase_3_connection_tests(),
            self.phase_4_configuration_validation(),
            self.phase_5_file_system_check()
        ])
        
        # Store results
        for i, phase in enumerate(phases, 1):
            self.results["phases"][f"phase_{i}"] = phase
        
        # Calculate summary
        total_passed = sum(phase["passed"] for phase in phases)
        total_failed = sum(phase["failed"] for phase in phases)
        total_warnings = sum(len(phase["warnings"]) for phase in phases)
        
        self.results["summary"]["total_checks"] = total_passed + total_failed
        self.results["summary"]["passed"] = total_passed
        self.results["summary"]["failed"] = total_failed
        self.results["summary"]["warnings"] = total_warnings
        
        # Determine overall status
        critical_failures = any(phase["status"] == "failed" for phase in phases)
        warnings_present = total_warnings > 0
        
        if critical_failures:
            self.results["summary"]["overall_status"] = "failed"
        elif warnings_present:
            self.results["summary"]["overall_status"] = "warning"
        else:
            self.results["summary"]["overall_status"] = "success"
        
        # Print final summary
        self.print_final_summary(time.time() - start_time)
        
        return self.results
    
    def print_final_summary(self, duration: float):
        """Print final summary."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Final Summary{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")
        
        status = self.results["summary"]["overall_status"]
        if status == "success":
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 Environment Ready!{Colors.END}")
            print(f"{Colors.GREEN}All checks passed successfully{Colors.END}")
        elif status == "warning":
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Environment Ready with Warnings{Colors.END}")
            print(f"{Colors.YELLOW}Can start application but review warnings{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ Environment Not Ready{Colors.END}")
            print(f"{Colors.RED}Cannot start application - fix errors first{Colors.END}")
        
        print(f"\n{Colors.BOLD}Statistics:{Colors.END}")
        print(f"  Total checks: {self.results['summary']['total_checks']}")
        print(f"  Passed: {self.results['summary']['passed']}")
        print(f"  Failed: {self.results['summary']['failed']}")
        print(f"  Warnings: {self.results['summary']['warnings']}")
        print(f"  Duration: {duration:.2f}s")
        
        # Print recommendations
        if self.results["recommendations"]:
            print(f"\n{Colors.YELLOW}💡 Recommendations:{Colors.END}")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"  {i}. {rec}")
        
        # Print next steps
        print(f"\n{Colors.CYAN}🚀 Next Steps:{Colors.END}")
        if status == "success":
            print("  Start the application: uvicorn app.main:app --reload")
            print("  Access API docs: http://localhost:8000/docs")
            print("  Check health: curl http://localhost:8000/health")
        elif status == "warning":
            print("  Review warnings above")
            print("  Start application: uvicorn app.main:app --reload")
            print("  Monitor logs for issues")
        else:
            print("  Fix all errors above")
            print("  Run: python scripts/fix_env.py")
            print("  Re-run: python scripts/preflight_check.py")
    
    def save_json_report(self, output_file: str):
        """Save JSON report to file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            self.print_status(f"JSON report saved to {output_file}", "success")
        except Exception as e:
            self.print_status(f"Failed to save JSON report: {e}", "error")
    
    def get_exit_code(self) -> int:
        """Get exit code based on results."""
        status = self.results["summary"]["overall_status"]
        if status == "success":
            return 0
        elif status == "warning":
            return 2
        else:
            return 1


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Comprehensive pre-flight check")
    parser.add_argument("--skip-connections", action="store_true", 
                       help="Skip connection tests")
    parser.add_argument("--skip-dependencies", action="store_true", 
                       help="Skip dependency checks")
    parser.add_argument("--json-output", type=str, 
                       help="Save JSON report to file")
    parser.add_argument("--fix-permissions", action="store_true", 
                       help="Attempt to fix file permissions")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--ci", action="store_true", 
                       help="CI mode (non-interactive)")
    parser.add_argument("--project-root", type=str, default=".", 
                       help="Project root directory")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    
    if not project_root.exists():
        print(f"{Colors.RED}❌ Project root not found: {project_root}{Colors.END}")
        sys.exit(1)
    
    checker = PreflightChecker(
        project_root=project_root,
        skip_connections=args.skip_connections,
        skip_dependencies=args.skip_dependencies,
        verbose=args.verbose,
        ci_mode=args.ci,
        fix_permissions=args.fix_permissions
    )
    
    try:
        results = await checker.run_all_checks()
        
        if args.json_output:
            checker.save_json_report(args.json_output)
        
        sys.exit(checker.get_exit_code())
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Pre-flight check interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Unexpected error during pre-flight check: {e}{Colors.END}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
