#!/usr/bin/env python3
"""
Comprehensive test execution script for the AI Web Scraper project.

This script provides systematic test execution with detailed reporting,
failure analysis, and coverage metrics. It runs tests in phases and
generates comprehensive reports for debugging and improvement.

Usage:
    python scripts/run_tests.py [options]

Options:
    --file <filename>     Run tests from specific file only
    --marker <marker>     Run tests with specific marker (unit, integration, slow)
    --coverage            Enable coverage reporting
    --verbose             Show detailed output
    --stop-on-failure     Stop execution on first failure
    --parallel            Run tests in parallel using pytest-xdist
    --output <format>     Specify output format (json, html, markdown)
    --phase <phase>       Run specific test phase (unit, integration, services, performance)
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import tempfile
import shutil


class TestRunner:
    """Comprehensive test execution and reporting system."""
    
    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent.parent
        self.results = {
            'execution_time': 0,
            'phases': {},
            'failures': [],
            'coverage': {},
            'summary': {}
        }
        self.start_time = None
        
    def run(self) -> int:
        """Main execution method."""
        self.start_time = time.time()
        
        try:
            # Environment validation
            if not self._validate_environment():
                return 2
            
            # Run test phases
            exit_code = self._run_test_phases()
            
            # Generate reports
            self._generate_reports()
            
            return exit_code
            
        except KeyboardInterrupt:
            print("\n❌ Test execution interrupted by user")
            return 1
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return 2
        finally:
            self.results['execution_time'] = time.time() - self.start_time
    
    def _validate_environment(self) -> bool:
        """Validate testing environment."""
        print("🔍 Validating test environment...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ required")
            return False
        
        # Check required packages
        required_packages = [
            'pytest', 'pytest-asyncio', 'pytest-cov', 'pytest-timeout'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing required packages: {', '.join(missing_packages)}")
            print("Install with: pip install -r requirements.txt")
            return False
        
        # Check optional environment variables
        env_warnings = []
        if not os.getenv('GEMINI_API_KEY'):
            env_warnings.append("GEMINI_API_KEY not set (some tests will be skipped)")
        if not os.getenv('MONGODB_URI'):
            env_warnings.append("MONGODB_URI not set (some tests will be skipped)")
        
        if env_warnings:
            print("⚠️  Environment warnings:")
            for warning in env_warnings:
                print(f"   {warning}")
        
        print("✅ Environment validation passed")
        return True
    
    def _run_test_phases(self) -> int:
        """Run tests in systematic phases."""
        phases = self._get_test_phases()
        overall_exit_code = 0
        
        for phase_name, phase_config in phases.items():
            if self.args.phase and self.args.phase != phase_name:
                continue
                
            print(f"\n🚀 Running {phase_name} tests...")
            phase_result = self._run_phase(phase_name, phase_config)
            self.results['phases'][phase_name] = phase_result
            
            if phase_result['exit_code'] != 0:
                overall_exit_code = 1
                if self.args.stop_on_failure:
                    break
        
        return overall_exit_code
    
    def _get_test_phases(self) -> Dict[str, Dict]:
        """Define test execution phases."""
        return {
            'unit': {
                'marker': 'unit',
                'description': 'Unit tests (no external dependencies)',
                'files': ['test_agents.py', 'test_scraper.py', 'test_processing.py', 'test_database.py', 'test_api.py']
            },
            'integration': {
                'marker': 'integration',
                'description': 'Integration tests with mocked services',
                'files': ['test_agents.py', 'test_scraper.py', 'test_processing.py', 'test_database.py', 'test_api.py']
            },
            'services': {
                'marker': 'requires_gemini or requires_mongodb',
                'description': 'Tests requiring actual services',
                'files': ['test_agents.py', 'test_scraper.py', 'test_processing.py', 'test_database.py']
            },
            'performance': {
                'marker': 'slow or performance',
                'description': 'Performance and load tests',
                'files': ['test_scraper.py', 'test_processing.py', 'test_database.py']
            }
        }
    
    def _run_phase(self, phase_name: str, phase_config: Dict) -> Dict:
        """Run a specific test phase."""
        phase_start = time.time()
        phase_result = {
            'name': phase_name,
            'description': phase_config['description'],
            'start_time': phase_start,
            'end_time': None,
            'duration': 0,
            'files': {},
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'exit_code': 0
        }
        
        # Build pytest command
        cmd = self._build_pytest_command(phase_config)
        
        # Run tests for each file individually
        for test_file in phase_config['files']:
            if self.args.file and self.args.file != test_file:
                continue
                
            file_result = self._run_test_file(test_file, cmd)
            phase_result['files'][test_file] = file_result
            
            # Aggregate results
            phase_result['total_tests'] += file_result['total_tests']
            phase_result['passed'] += file_result['passed']
            phase_result['failed'] += file_result['failed']
            phase_result['skipped'] += file_result['skipped']
            phase_result['errors'] += file_result['errors']
            
            if file_result['exit_code'] != 0:
                phase_result['exit_code'] = 1
        
        phase_result['end_time'] = time.time()
        phase_result['duration'] = phase_result['end_time'] - phase_result['start_time']
        
        # Print phase summary
        self._print_phase_summary(phase_result)
        
        return phase_result
    
    def _build_pytest_command(self, phase_config: Dict) -> List[str]:
        """Build pytest command for a phase."""
        cmd = ['python3', '-m', 'pytest']
        
        # Add marker filter - prefer CLI marker over phase config marker
        marker = self.args.marker if self.args.marker else phase_config.get('marker')
        if marker:
            cmd.extend(['-m', marker])
        
        # Add verbosity
        if self.args.verbose:
            cmd.append('-vv')
        else:
            cmd.append('-v')
        
        # Add coverage
        if self.args.coverage:
            cmd.extend(['--cov=app', '--cov-report=term', '--cov-report=html', '--cov-report=xml', '--cov-fail-under=70'])
        
        # Add timeout
        cmd.extend(['--timeout=30'])
        
        # Add parallel execution
        if self.args.parallel:
            cmd.extend(['-n', 'auto'])
        
        # Add stop on failure
        if self.args.stop_on_failure:
            cmd.append('-x')
        
        return cmd
    
    def _run_test_file(self, test_file: str, base_cmd: List[str]) -> Dict:
        """Run tests for a specific file."""
        file_path = self.project_root / 'tests' / test_file
        if not file_path.exists():
            return {
                'file': test_file,
                'status': 'skipped',
                'reason': 'File not found',
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 1,
                'errors': 0,
                'exit_code': 0,
                'duration': 0,
                'output': '',
                'failures': []
            }
        
        cmd = base_cmd + [str(file_path)]
        
        print(f"  📁 Running {test_file}...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per file
                cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            file_result = self._parse_pytest_output(test_file, result, duration)
            
            # Print file summary
            status_emoji = "✅" if file_result['exit_code'] == 0 else "❌"
            print(f"    {status_emoji} {file_result['total_tests']} tests, "
                  f"{file_result['passed']} passed, {file_result['failed']} failed, "
                  f"{file_result['skipped']} skipped ({duration:.1f}s)")
            
            return file_result
            
        except subprocess.TimeoutExpired:
            print(f"    ⏰ Timeout after 5 minutes")
            return {
                'file': test_file,
                'status': 'timeout',
                'reason': 'Test execution timeout',
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': 1,
                'exit_code': 1,
                'duration': 300,
                'output': 'Test execution timed out',
                'failures': [{'test': 'all', 'error': 'Timeout after 5 minutes'}]
            }
        except Exception as e:
            print(f"    ❌ Error running tests: {e}")
            return {
                'file': test_file,
                'status': 'error',
                'reason': str(e),
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': 1,
                'exit_code': 1,
                'duration': time.time() - start_time,
                'output': str(e),
                'failures': [{'test': 'all', 'error': str(e)}]
            }
    
    def _parse_pytest_output(self, test_file: str, result: subprocess.CompletedProcess, duration: float) -> Dict:
        """Parse pytest output to extract test results using robust regex."""
        import re
        
        output = result.stdout + result.stderr
        
        # Initialize counters
        total_tests = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = 0
        
        # Robust regex patterns for pytest summary lines
        # Handles various formats like:
        # "5 passed, 2 failed, 1 skipped in 1.23s"
        # "3 passed, 1 error in 0.45s"
        # "10 passed, 2 failed, 1 skipped, 1 xfailed, 1 xpassed, 2 warnings in 2.34s"
        summary_patterns = [
            r'(\d+)\s+passed',
            r'(\d+)\s+failed', 
            r'(\d+)\s+skipped',
            r'(\d+)\s+error(?:s)?',
            r'(\d+)\s+xfailed',
            r'(\d+)\s+xpassed',
            r'(\d+)\s+warnings?'
        ]
        
        # Find the last summary line (usually at the end)
        lines = output.split('\n')
        summary_line = None
        
        for line in reversed(lines):
            if any(keyword in line.lower() for keyword in ['passed', 'failed', 'skipped', 'error', 'warnings']):
                if 'in ' in line and ('s' in line or 'seconds' in line):
                    summary_line = line
                    break
        
        if summary_line:
            # Extract counts using regex
            for pattern in summary_patterns:
                match = re.search(pattern, summary_line)
                if match:
                    count = int(match.group(1))
                    if 'passed' in pattern:
                        passed = count
                    elif 'failed' in pattern:
                        failed = count
                    elif 'skipped' in pattern:
                        skipped = count
                    elif 'error' in pattern:
                        errors = count
        
        total_tests = passed + failed + skipped + errors
        
        # Extract failure details
        failures = []
        if failed > 0 or errors > 0:
            failures = self._extract_failure_details(output)
        
        return {
            'file': test_file,
            'status': 'completed',
            'reason': 'Tests completed',
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'errors': errors,
            'exit_code': result.returncode,
            'duration': duration,
            'output': output,
            'failures': failures
        }
    
    def _extract_failure_details(self, output: str) -> List[Dict]:
        """Extract detailed failure information from pytest output."""
        failures = []
        lines = output.split('\n')
        
        current_failure = None
        for line in lines:
            if line.startswith('FAILED'):
                if current_failure:
                    failures.append(current_failure)
                current_failure = {
                    'test': line.split()[1] if len(line.split()) > 1 else 'unknown',
                    'error': '',
                    'traceback': []
                }
            elif line.startswith('ERROR'):
                if current_failure:
                    failures.append(current_failure)
                current_failure = {
                    'test': line.split()[1] if len(line.split()) > 1 else 'unknown',
                    'error': '',
                    'traceback': []
                }
            elif current_failure:
                if line.strip():
                    current_failure['traceback'].append(line)
                    if 'Error:' in line or 'Exception:' in line:
                        current_failure['error'] = line.strip()
        
        if current_failure:
            failures.append(current_failure)
        
        return failures
    
    def _parse_coverage_xml(self) -> Dict:
        """Parse coverage.xml to extract coverage metrics."""
        import xml.etree.ElementTree as ET
        
        coverage_path = self.project_root / 'coverage.xml'
        if not coverage_path.exists():
            return {}
        
        try:
            tree = ET.parse(coverage_path)
            root = tree.getroot()
            
            # Extract overall coverage
            total_lines = int(root.get('lines-valid', 0))
            covered_lines = int(root.get('lines-covered', 0))
            
            coverage_percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0
            
            # Extract per-module coverage
            module_coverage = {}
            for package in root.findall('.//package'):
                package_name = package.get('name', 'unknown')
                package_lines = int(package.get('lines-valid', 0))
                package_covered = int(package.get('lines-covered', 0))
                package_percent = (package_covered / package_lines * 100) if package_lines > 0 else 0
                
                module_coverage[package_name] = {
                    'total_lines': package_lines,
                    'covered_lines': package_covered,
                    'coverage_percent': package_percent
                }
            
            return {
                'total_coverage_percent': coverage_percent,
                'total_lines': total_lines,
                'covered_lines': covered_lines,
                'module_coverage': module_coverage
            }
            
        except Exception as e:
            print(f"Warning: Could not parse coverage.xml: {e}")
            return {}
    
    def _print_phase_summary(self, phase_result: Dict):
        """Print summary for a test phase."""
        total = phase_result['total_tests']
        passed = phase_result['passed']
        failed = phase_result['failed']
        skipped = phase_result['skipped']
        errors = phase_result['errors']
        duration = phase_result['duration']
        
        if total == 0:
            print(f"  ⚠️  No tests found for {phase_result['name']}")
            return
        
        pass_rate = (passed / total) * 100 if total > 0 else 0
        
        status_emoji = "✅" if failed == 0 and errors == 0 else "❌"
        print(f"  {status_emoji} {phase_result['name'].title()} Phase: "
              f"{passed}/{total} passed ({pass_rate:.1f}%), "
              f"{failed} failed, {skipped} skipped ({duration:.1f}s)")
    
    def _generate_reports(self):
        """Generate comprehensive test reports."""
        print("\n📊 Generating test reports...")
        
        # Parse coverage if enabled
        if self.args.coverage:
            coverage_data = self._parse_coverage_xml()
            self.results['coverage'] = coverage_data
        
        # Calculate overall summary
        self._calculate_summary()
        
        # Generate reports based on output format
        if self.args.output == 'json':
            self._generate_json_report()
        elif self.args.output == 'html':
            self._generate_html_report()
        elif self.args.output == 'markdown':
            self._generate_markdown_report()
        else:
            # Default: generate all formats
            self._generate_json_report()
            self._generate_markdown_report()
        
        # Print final summary
        self._print_final_summary()
    
    def _calculate_summary(self):
        """Calculate overall test summary."""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_errors = 0
        
        for phase_result in self.results['phases'].values():
            total_tests += phase_result['total_tests']
            total_passed += phase_result['passed']
            total_failed += phase_result['failed']
            total_skipped += phase_result['skipped']
            total_errors += phase_result['errors']
        
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed': total_passed,
            'failed': total_failed,
            'skipped': total_skipped,
            'errors': total_errors,
            'pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'execution_time': self.results['execution_time']
        }
    
    def _generate_json_report(self):
        """Generate JSON test report."""
        report_path = self.project_root / 'test_results.json'
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"  📄 JSON report: {report_path}")
    
    def _generate_html_report(self):
        """Generate HTML test report."""
        # This would generate a comprehensive HTML report
        # For now, just create a placeholder
        report_path = self.project_root / 'test_results.html'
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Results - AI Web Scraper</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .phase {{ margin: 10px 0; padding: 10px; border-left: 4px solid #007cba; }}
                .failed {{ border-left-color: #dc3545; }}
                .passed {{ border-left-color: #28a745; }}
            </style>
        </head>
        <body>
            <h1>Test Results - AI Web Scraper</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Tests: {self.results['summary']['total_tests']}</p>
                <p>Passed: {self.results['summary']['passed']}</p>
                <p>Failed: {self.results['summary']['failed']}</p>
                <p>Skipped: {self.results['summary']['skipped']}</p>
                <p>Pass Rate: {self.results['summary']['pass_rate']:.1f}%</p>
                <p>Execution Time: {self.results['summary']['execution_time']:.1f}s</p>
            </div>
        </body>
        </html>
        """
        with open(report_path, 'w') as f:
            f.write(html_content)
        print(f"  📄 HTML report: {report_path}")
    
    def _generate_markdown_report(self):
        """Generate Markdown test report."""
        report_path = self.project_root / 'docs' / 'TEST_RESULTS.md'
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(self._create_markdown_content())
        print(f"  📄 Markdown report: {report_path}")
    
    def _create_markdown_content(self) -> str:
        """Create markdown content for test report."""
        summary = self.results['summary']
        coverage = self.results.get('coverage', {})
        
        content = f"""# Test Results Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

- **Total Tests:** {summary['total_tests']}
- **Passed:** {summary['passed']}
- **Failed:** {summary['failed']}
- **Skipped:** {summary['skipped']}
- **Pass Rate:** {summary['pass_rate']:.1f}%
- **Execution Time:** {summary['execution_time']:.1f}s
- **Coverage:** {coverage.get('total_coverage_percent', 0):.1f}%

## Test Results by Module

"""
        
        # Generate module-level results
        module_stats = {}
        for phase_name, phase_result in self.results['phases'].items():
            for file_name, file_result in phase_result['files'].items():
                if file_name not in module_stats:
                    module_stats[file_name] = {
                        'tests': 0, 'passed': 0, 'failed': 0, 'skipped': 0,
                        'time': 0, 'coverage': 0
                    }
                
                module_stats[file_name]['tests'] += file_result['total_tests']
                module_stats[file_name]['passed'] += file_result['passed']
                module_stats[file_name]['failed'] += file_result['failed']
                module_stats[file_name]['skipped'] += file_result['skipped']
                module_stats[file_name]['time'] += file_result['duration']
        
        # Add module coverage if available
        if coverage.get('module_coverage'):
            for module_name, module_cov in coverage['module_coverage'].items():
                # Map module names to test files
                test_file = f"test_{module_name.split('.')[-1]}.py"
                if test_file in module_stats:
                    module_stats[test_file]['coverage'] = module_cov['coverage_percent']
        
        for module_name, stats in module_stats.items():
            content += f"""### {module_name}
- **Tests:** {stats['tests']}
- **Passed:** {stats['passed']}
- **Failed:** {stats['failed']}
- **Skipped:** {stats['skipped']}
- **Execution Time:** {stats['time']:.1f}s
- **Coverage:** {stats['coverage']:.1f}%

"""
        
        content += """## Failed Tests Details

### Critical Failures (Blocking Functionality)
"""
        
        # Categorize failures by type
        critical_failures = []
        import_errors = []
        assertion_failures = []
        timeout_errors = []
        mock_errors = []
        async_errors = []
        
        for phase_name, phase_result in self.results['phases'].items():
            for file_name, file_result in phase_result['files'].items():
                for failure in file_result['failures']:
                    error_text = failure.get('error', '').lower()
                    if 'import' in error_text or 'module' in error_text:
                        import_errors.append(f"{file_name}: {failure['test']}")
                    elif 'timeout' in error_text:
                        timeout_errors.append(f"{file_name}: {failure['test']}")
                    elif 'mock' in error_text or 'patch' in error_text:
                        mock_errors.append(f"{file_name}: {failure['test']}")
                    elif 'async' in error_text or 'await' in error_text:
                        async_errors.append(f"{file_name}: {failure['test']}")
                    elif 'assert' in error_text:
                        assertion_failures.append(f"{file_name}: {failure['test']}")
                    else:
                        critical_failures.append(f"{file_name}: {failure['test']}")
        
        if critical_failures:
            content += "\n".join(f"- {failure}" for failure in critical_failures) + "\n"
        else:
            content += "None\n"
        
        content += """
### Import Errors
"""
        if import_errors:
            content += "\n".join(f"- {error}" for error in import_errors) + "\n"
        else:
            content += "None\n"
        
        content += """
### Assertion Failures
"""
        if assertion_failures:
            content += "\n".join(f"- {failure}" for failure in assertion_failures) + "\n"
        else:
            content += "None\n"
        
        content += """
### Timeout Errors
"""
        if timeout_errors:
            content += "\n".join(f"- {error}" for error in timeout_errors) + "\n"
        else:
            content += "None\n"
        
        content += """
### Mock Configuration Issues
"""
        if mock_errors:
            content += "\n".join(f"- {error}" for error in mock_errors) + "\n"
        else:
            content += "None\n"
        
        content += """
### Async/Await Problems
"""
        if async_errors:
            content += "\n".join(f"- {error}" for error in async_errors) + "\n"
        else:
            content += "None\n"
        
        content += """
## Coverage Report

### Overall Coverage
"""
        if coverage:
            content += f"""- **Total Coverage:** {coverage.get('total_coverage_percent', 0):.1f}%
- **Lines Covered:** {coverage.get('covered_lines', 0)}
- **Lines Missing:** {coverage.get('total_lines', 0) - coverage.get('covered_lines', 0)}

### Coverage by Module
"""
            for module_name, module_cov in coverage.get('module_coverage', {}).items():
                content += f"- **{module_name}:** {module_cov['coverage_percent']:.1f}%\n"
        else:
            content += "- **Total Coverage:** Not available\n- **Lines Covered:** Not available\n- **Lines Missing:** Not available\n"
        
        content += """
## Performance Metrics

### Slowest Tests (Top 10)
"""
        # Find slowest tests
        all_tests = []
        for phase_name, phase_result in self.results['phases'].items():
            for file_name, file_result in phase_result['files'].items():
                all_tests.append((file_name, file_result['duration']))
        
        slowest_tests = sorted(all_tests, key=lambda x: x[1], reverse=True)[:10]
        for test_file, duration in slowest_tests:
            content += f"- {test_file}: {duration:.2f}s\n"
        
        content += """
## Recommendations

### Priority Fixes (Critical Failures Blocking Functionality)
1. Address critical test failures blocking functionality
2. Fix import errors and dependency issues
3. Improve mock configuration consistency

### Code Quality Improvements
1. **Test Coverage:** Increase coverage to meet 70% minimum threshold
2. **Mock Consistency:** Standardize mock patterns across all test files
3. **Error Handling:** Improve error handling in test fixtures
4. **Documentation:** Add docstrings to test methods explaining purpose

## Next Steps

### Immediate Actions (This Week)
- [ ] Fix critical test failures blocking functionality
- [ ] Address import errors and dependency issues
- [ ] Improve mock configuration consistency
- [ ] Add missing test cases for uncovered code

### Short-term Goals (Next 2 Weeks)
- [ ] Achieve 70% minimum test coverage
- [ ] Optimize test execution time
- [ ] Expand integration test coverage
- [ ] Create comprehensive test documentation

### Long-term Goals (Next Month)
- [ ] Implement continuous integration improvements
- [ ] Add performance benchmarking tests
- [ ] Create automated test result analysis
- [ ] Establish test quality metrics and monitoring

## Appendix

### Test Execution Command Used
```bash
python scripts/run_tests.py --coverage --output markdown --verbose
```

### Environment Details
- **Python Version:** {sys.version.split()[0]}
- **Operating System:** {os.name}
- **Test Framework:** pytest

### Coverage HTML Report Location
- **File:** `htmlcov/index.html`

---
*This report was generated automatically by the AI Web Scraper test execution system.*
"""
        
        return content
    
    def _print_final_summary(self):
        """Print final test execution summary."""
        summary = self.results['summary']
        
        print(f"\n🎯 Test Execution Complete")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed']} ({summary['pass_rate']:.1f}%)")
        print(f"   Failed: {summary['failed']}")
        print(f"   Skipped: {summary['skipped']}")
        print(f"   Execution Time: {summary['execution_time']:.1f}s")
        
        if summary['failed'] > 0:
            print(f"\n❌ {summary['failed']} tests failed - see reports for details")
            return 1
        else:
            print(f"\n✅ All tests passed!")
            return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Comprehensive test execution for AI Web Scraper')
    
    parser.add_argument('--file', help='Run tests from specific file only')
    parser.add_argument('--marker', help='Run tests with specific marker (unit, integration, slow)')
    parser.add_argument('--coverage', action='store_true', help='Enable coverage reporting')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('--stop-on-failure', action='store_true', help='Stop execution on first failure')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel using pytest-xdist')
    parser.add_argument('--output', choices=['json', 'html', 'markdown'], default='markdown', 
                       help='Specify output format')
    parser.add_argument('--phase', help='Run specific test phase (unit, integration, services, performance)')
    
    args = parser.parse_args()
    
    runner = TestRunner(args)
    exit_code = runner.run()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
