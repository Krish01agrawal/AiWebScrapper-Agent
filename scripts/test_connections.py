#!/usr/bin/env python3
"""
Connection testing script for AI Web Scraper project.

This script tests MongoDB and Gemini API connectivity using existing
functions from the codebase. It provides detailed connection reports
with latency metrics and error handling.

Usage:
    python scripts/test_connections.py
    python scripts/test_connections.py --mongodb-only
    python scripts/test_connections.py --gemini-only
    python scripts/test_connections.py --verbose --timeout 10

Exit codes:
    0 - All connections successful
    1 - Connection failures
"""

import asyncio
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import argparse

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
    from motor.motor_asyncio import AsyncIOMotorClient
    import google.generativeai as genai
    from app.core.config import get_settings
    from scripts.utils import Colors, print_status
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the project root and dependencies are installed")
    sys.exit(1)


class ConnectionTester:
    """Connection testing class."""
    
    def __init__(self, timeout: int = 5, verbose: bool = False, gemini_model: Optional[str] = None, mongodb_uri: Optional[str] = None):
        self.timeout = timeout
        self.verbose = verbose
        self.gemini_model = gemini_model
        self.mongodb_uri = mongodb_uri
        self.results: Dict[str, Any] = {}
        
    async def test_mongodb_connection(self) -> Dict[str, Any]:
        """Test MongoDB connection."""
        result = {
            "service": "MongoDB",
            "status": "unknown",
            "latency_ms": None,
            "error": None,
            "details": {}
        }
        
        # Initialize client to None to ensure it's defined
        client = None
        
        try:
            print_status("Testing MongoDB connection...", "info")
            
            # Load settings
            settings = get_settings()
            
            # Determine MongoDB URI to use
            mongodb_uri = self.mongodb_uri or settings.mongodb_uri or "mongodb://localhost:27017"
            
            if not mongodb_uri:
                result["error"] = "MONGODB_URI not configured"
                result["status"] = "failed"
                return result
            
            # Create client with timeout
            start_time = time.time()
            client = AsyncIOMotorClient(
                mongodb_uri,
                serverSelectionTimeoutMS=self.timeout * 1000,
                connectTimeoutMS=self.timeout * 1000,
                socketTimeoutMS=self.timeout * 1000
            )
            
            # Test connection with ping
            await client.admin.command('ping')
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            result["latency_ms"] = round(latency_ms, 2)
            
            # Test database access
            if settings.mongodb_db:
                db = client[settings.mongodb_db]
                collections = await db.list_collection_names()
                result["details"]["collections_count"] = len(collections)
                result["details"]["database"] = settings.mongodb_db
            
            # Close client
            client.close()
            
            result["status"] = "success"
            result["details"]["uri_tested"] = mongodb_uri
            print_status(f"MongoDB connected successfully ({latency_ms:.2f}ms) to {mongodb_uri}", "success")
            
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
            
            # Categorize error
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                result["details"]["error_type"] = "timeout"
                print_status("MongoDB connection timeout", "error")
            elif "authentication" in error_msg or "auth" in error_msg:
                result["details"]["error_type"] = "authentication"
                print_status("MongoDB authentication failed", "error")
            elif "network" in error_msg or "unreachable" in error_msg:
                result["details"]["error_type"] = "network"
                print_status("MongoDB network unreachable", "error")
            elif "uri" in error_msg or "invalid" in error_msg:
                result["details"]["error_type"] = "invalid_uri"
                print_status("MongoDB URI format invalid", "error")
            else:
                result["details"]["error_type"] = "unknown"
                print_status(f"MongoDB connection failed: {e}", "error")
            
            if self.verbose:
                print(f"{Colors.RED}Stack trace:{Colors.END}")
                traceback.print_exc()
        
        finally:
            # Ensure client is closed on both success and failure paths
            if client is not None:
                client.close()
        
        return result
    
    async def test_gemini_connection(self) -> Dict[str, Any]:
        """Test Gemini API connection."""
        result = {
            "service": "Gemini API",
            "status": "unknown",
            "latency_ms": None,
            "error": None,
            "details": {}
        }
        
        # Define model_name before try block to avoid UnboundLocalError
        model_name = self.gemini_model or os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        
        try:
            print_status("Testing Gemini API connection...", "info")
            
            # Load settings
            settings = get_settings()
            
            if not settings.gemini_api_key:
                result["error"] = "GEMINI_API_KEY not configured"
                result["status"] = "failed"
                return result
            
            # Configure Gemini API
            genai.configure(api_key=settings.gemini_api_key)
            
            # Create model
            model = genai.GenerativeModel(model_name)
            
            # Test with lightweight request and explicit generation config
            start_time = time.time()
            generation_config = {
                'max_output_tokens': 50,
                'temperature': 0.1
            }
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    "Test connection. Respond with 'OK'.",
                    generation_config=generation_config
                ),
                timeout=self.timeout
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            result["latency_ms"] = round(latency_ms, 2)
            
            # Verify response
            if response and response.text:
                result["details"]["response_text"] = response.text.strip()
                result["details"]["model_used"] = model_name
                result["status"] = "success"
                print_status(f"Gemini API connected successfully ({latency_ms:.2f}ms) using {model_name}", "success")
            else:
                result["error"] = f"Empty response from Gemini API (model: {model_name})"
                result["status"] = "failed"
                result["details"]["model_used"] = model_name
                print_status(f"Gemini API returned empty response (model: {model_name})", "error")
            
        except asyncio.TimeoutError:
            result["error"] = f"Request timeout after {self.timeout} seconds (model: {model_name})"
            result["status"] = "failed"
            result["details"]["error_type"] = "timeout"
            result["details"]["model_used"] = model_name
            print_status(f"Gemini API request timeout (model: {model_name})", "error")
            
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
            result["details"]["model_used"] = model_name
            
            # Categorize error with improved parsing
            error_msg = str(e).lower()
            if "api key" in error_msg or "invalid" in error_msg or "unauthorized" in error_msg:
                result["details"]["error_type"] = "invalid_api_key"
                print_status("Gemini API key invalid", "error")
            elif "quota" in error_msg or "limit" in error_msg or "rate" in error_msg:
                result["details"]["error_type"] = "quota_exceeded"
                print_status("Gemini API quota exceeded", "error")
            elif "network" in error_msg or "connection" in error_msg or "timeout" in error_msg:
                result["details"]["error_type"] = "network"
                print_status("Gemini API network error", "error")
            elif "model" in error_msg or "not found" in error_msg or "does not exist" in error_msg:
                result["details"]["error_type"] = "model_not_found"
                print_status(f"Gemini model '{model_name}' not found - try 'gemini-1.5-flash' as fallback", "error")
            elif "permission" in error_msg or "forbidden" in error_msg:
                result["details"]["error_type"] = "permission_denied"
                print_status("Gemini API permission denied", "error")
            elif "bad request" in error_msg or "400" in error_msg:
                result["details"]["error_type"] = "bad_request"
                print_status("Gemini API bad request", "error")
            else:
                result["details"]["error_type"] = "unknown"
                print_status(f"Gemini API connection failed: {e}", "error")
            
            if self.verbose:
                print(f"{Colors.RED}Stack trace:{Colors.END}")
                traceback.print_exc()
        
        return result
    
    async def test_all_connections(self, mongodb_only: bool = False, gemini_only: bool = False) -> Dict[str, Any]:
        """Test all connections."""
        print(f"{Colors.BOLD}{Colors.CYAN}🔗 Connection Test Report{Colors.END}")
        print(f"{Colors.CYAN}{'='*50}{Colors.END}")
        
        tasks = []
        
        if not gemini_only:
            tasks.append(self.test_mongodb_connection())
        
        if not mongodb_only:
            tasks.append(self.test_gemini_connection())
        
        if not tasks:
            print(f"{Colors.YELLOW}⚠️  No connections to test{Colors.END}")
            return {}
        
        # Run tests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_name = "MongoDB" if i == 0 and not gemini_only else "Gemini API"
                self.results[service_name] = {
                    "service": service_name,
                    "status": "failed",
                    "error": str(result),
                    "latency_ms": None,
                    "details": {"error_type": "exception"}
                }
            else:
                self.results[result["service"]] = result
        
        return self.results
    
    def print_summary(self) -> None:
        """Print connection test summary."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Connection Summary{Colors.END}")
        print(f"{Colors.CYAN}{'='*50}{Colors.END}")
        
        success_count = 0
        total_count = len(self.results)
        
        for service, result in self.results.items():
            if result["status"] == "success":
                success_count += 1
                latency = result.get("latency_ms", "N/A")
                print(f"{Colors.GREEN}✅ {service}: Connected ({latency}ms){Colors.END}")
                
                # Print additional details
                if result.get("details"):
                    details = result["details"]
                    if "collections_count" in details:
                        print(f"   Database: {details.get('database', 'N/A')}")
                        print(f"   Collections: {details.get('collections_count', 0)}")
                    if "response_text" in details:
                        print(f"   Response: {details['response_text']}")
            else:
                print(f"{Colors.RED}❌ {service}: Failed{Colors.END}")
                if result.get("error"):
                    print(f"   Error: {result['error']}")
                if result.get("details", {}).get("error_type"):
                    print(f"   Type: {result['details']['error_type']}")
        
        print(f"\n{Colors.BOLD}Results: {success_count}/{total_count} connections successful{Colors.END}")
        
        if success_count == total_count:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 All connections successful!{Colors.END}")
        elif success_count > 0:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Partial connectivity{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ All connections failed{Colors.END}")
            print(f"\n{Colors.YELLOW}💡 Troubleshooting tips:{Colors.END}")
            print("   1. Check your internet connection")
            print("   2. Verify API keys and credentials")
            print("   3. Check firewall and proxy settings")
            print("   4. Review environment configuration")
            print("   5. Run 'python scripts/validate_env.py' to check config")
    
    def get_exit_code(self) -> int:
        """Get exit code based on results."""
        if not self.results:
            return 1
        
        failed_count = sum(1 for result in self.results.values() if result["status"] != "success")
        return 0 if failed_count == 0 else 1


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test MongoDB and Gemini API connections")
    parser.add_argument("--mongodb-only", action="store_true", 
                       help="Test only MongoDB connection")
    parser.add_argument("--gemini-only", action="store_true", 
                       help="Test only Gemini API connection")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output with stack traces")
    parser.add_argument("--timeout", "-t", type=int, default=10, 
                       help="Connection timeout in seconds (default: 10)")
    parser.add_argument("--gemini-model", type=str, 
                       help="Override Gemini model (e.g., gemini-1.5-flash)")
    parser.add_argument("--mongodb-uri", type=str, 
                       help="Override MongoDB URI (default: mongodb://localhost:27017)")
    
    args = parser.parse_args()
    
    if args.mongodb_only and args.gemini_only:
        print(f"{Colors.RED}❌ Cannot specify both --mongodb-only and --gemini-only{Colors.END}")
        sys.exit(1)
    
    tester = ConnectionTester(timeout=args.timeout, verbose=args.verbose, gemini_model=args.gemini_model, mongodb_uri=args.mongodb_uri)
    
    try:
        await tester.test_all_connections(
            mongodb_only=args.mongodb_only,
            gemini_only=args.gemini_only
        )
        tester.print_summary()
        sys.exit(tester.get_exit_code())
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Connection test interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Unexpected error during connection test: {e}{Colors.END}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
