#!/usr/bin/env python3
"""
Shared utilities for scripts in the AI Web Scraper project.

This module provides common utilities used across multiple scripts,
including color formatting, common validation functions, and shared constants.
"""


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


def print_status(message: str, status: str = "info"):
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


def print_phase_header(phase_name: str, phase_number: int):
    """Print phase header."""
    print(f"\n{Colors.BOLD}{Colors.PURPLE}Phase {phase_number}: {phase_name}{Colors.END}")
    print(f"{Colors.PURPLE}{'='*60}{Colors.END}")
