#!/usr/bin/env python3
"""
Response schema validation utility for API responses.
Validates responses against expected Pydantic models.
"""
import json
import sys
import argparse
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

try:
    from pydantic import ValidationError, BaseModel
    from app.api.routers.scrape import ScrapeResponse, ScrapeRequest, ScrapeProgress, ScrapeError
    from app.api.schemas import APIResponse, ExecutionMetadata, ErrorDetail, ErrorResponse
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running from the project root and dependencies are installed")
    sys.exit(1)


class ResponseValidator:
    """Response schema validation class."""
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.errors = []
        self.warnings = []
    
    def validate_scrape_response(self, response_data: Dict[str, Any]) -> Tuple[bool, List[str], Optional[ScrapeResponse]]:
        """Validate response_data against ScrapeResponse model."""
        try:
            parsed_model = ScrapeResponse(**response_data)
            return True, [], parsed_model
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                errors.append(f"{field_path}: {error['msg']}")
            return False, errors, None
    
    def validate_execution_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate ExecutionMetadata structure."""
        errors = []
        
        required_fields = ["execution_time_ms"]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")
        
        if "execution_time_ms" in metadata:
            exec_time = metadata["execution_time_ms"]
            if not isinstance(exec_time, (int, float)) or exec_time < 0:
                errors.append("execution_time_ms must be a non-negative number")
        
        if "stages_timing" in metadata:
            stages = metadata["stages_timing"]
            if not isinstance(stages, dict):
                errors.append("stages_timing must be a dictionary")
            else:
                for stage, timing in stages.items():
                    if not isinstance(timing, (int, float)) or timing < 0:
                        errors.append(f"Invalid timing for stage {stage}: {timing}")
        
        return len(errors) == 0, errors
    
    def validate_query_structure(self, query_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate query object structure."""
        errors = []
        
        required_fields = ["text", "category", "confidence_score"]
        for field in required_fields:
            if field not in query_data:
                errors.append(f"Missing required field in query: {field}")
        
        if "category" in query_data:
            category = query_data["category"]
            # Validate category is a non-empty string, but don't hard-code allowed values
            # to allow for future category extensions
            if not isinstance(category, str) or not category:
                errors.append(f"Invalid category: {category}. Category must be a non-empty string")
        
        if "confidence_score" in query_data:
            confidence = query_data["confidence_score"]
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                errors.append(f"Invalid confidence_score: {confidence}. Must be between 0.0 and 1.0")
        
        return len(errors) == 0, errors
    
    def validate_results_structure(self, results_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate results object structure."""
        errors = []
        
        required_fields = ["total_items", "processed_items", "success_rate"]
        for field in required_fields:
            if field not in results_data:
                errors.append(f"Missing required field in results: {field}")
        
        if "total_items" in results_data:
            total = results_data["total_items"]
            if not isinstance(total, int) or total < 0:
                errors.append("total_items must be a non-negative integer")
        
        if "processed_items" in results_data:
            processed = results_data["processed_items"]
            if not isinstance(processed, int) or processed < 0:
                errors.append("processed_items must be a non-negative integer")
        
        if "success_rate" in results_data:
            success_rate = results_data["success_rate"]
            if not isinstance(success_rate, (int, float)) or not (0.0 <= success_rate <= 1.0):
                errors.append("success_rate must be between 0.0 and 1.0")
        
        if "processed_contents" in results_data:
            contents = results_data["processed_contents"]
            if not isinstance(contents, list):
                errors.append("processed_contents must be a list")
            else:
                # Validate each content item
                for i, item in enumerate(contents):
                    item_errors = self.validate_processed_content_item(item)
                    if item_errors:
                        errors.extend([f"processed_contents[{i}].{e}" for e in item_errors])
        
        return len(errors) == 0, errors
    
    def validate_analytics_structure(self, analytics_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate analytics object structure."""
        errors = []
        
        required_fields = ["pages_scraped", "processing_time_breakdown"]
        for field in required_fields:
            if field not in analytics_data:
                errors.append(f"Missing required field in analytics: {field}")
        
        if "pages_scraped" in analytics_data:
            pages = analytics_data["pages_scraped"]
            if not isinstance(pages, int) or pages < 0:
                errors.append("pages_scraped must be a non-negative integer")
        
        if "processing_time_breakdown" in analytics_data:
            breakdown = analytics_data["processing_time_breakdown"]
            if not isinstance(breakdown, dict):
                errors.append("processing_time_breakdown must be a dictionary")
            else:
                for stage, timing in breakdown.items():
                    if not isinstance(timing, (int, float)) or timing < 0:
                        errors.append(f"Invalid timing for stage {stage} in breakdown: {timing}")
        
        return len(errors) == 0, errors
    
    def validate_error_response(self, error_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate error response structure."""
        errors = []
        
        required_fields = ["code", "message"]
        for field in required_fields:
            if field not in error_data:
                errors.append(f"Missing required field in error: {field}")
        
        if "details" in error_data:
            details = error_data["details"]
            if not isinstance(details, list):
                errors.append("error.details must be a list")
            else:
                for i, detail in enumerate(details):
                    if not isinstance(detail, dict):
                        errors.append(f"error.details[{i}] must be a dictionary")
                    else:
                        if "error_code" not in detail:
                            errors.append(f"error.details[{i}] missing error_code")
                        if "message" not in detail:
                            errors.append(f"error.details[{i}] missing message")
        
        return len(errors) == 0, errors
    
    def validate_processed_content_item(self, item: Dict[str, Any]) -> List[str]:
        """Validate individual processed content item."""
        errors = []
        
        required_fields = ["original_content"]
        for field in required_fields:
            if field not in item:
                errors.append(f"Missing required field: {field}")
        
        if "original_content" in item:
            original = item["original_content"]
            if not isinstance(original, dict):
                errors.append("original_content must be a dictionary")
            else:
                if "url" not in original:
                    errors.append("original_content missing url")
                if "content" not in original:
                    errors.append("original_content missing content")
        
        return errors
    
    def validate_stage_timings(self, stage_timings: Dict[str, float], store_results: bool = True) -> Tuple[bool, List[str]]:
        """Validate stage timing structure.
        
        Args:
            stage_timings: Dictionary of stage names to timing values
            store_results: Whether database_storage stage should be expected (default: True)
        """
        errors = []
        
        expected_stages = ["query_processing", "web_scraping", "ai_processing"]
        
        # Database storage is expected when store_results=True
        if store_results:
            expected_stages.append("database_storage")
        
        missing_stages = [stage for stage in expected_stages if stage not in stage_timings]
        
        if missing_stages:
            errors.append(f"Missing expected stages: {missing_stages}")
        
        for stage, timing in stage_timings.items():
            if not isinstance(timing, (int, float)) or timing < 0:
                errors.append(f"Invalid timing for stage {stage}: {timing}")
        
        return len(errors) == 0, errors
    
    def validate_complete_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive validation of complete response."""
        validation_report = {
            "overall_status": "unknown",
            "errors": [],
            "warnings": [],
            "schema_compliance": 0.0
        }
        
        # Validate top-level structure
        if "status" not in response_data:
            validation_report["errors"].append("Missing required field: status")
            return validation_report
        
        status = response_data["status"]
        
        if status == "success":
            # Validate success response
            is_valid, errors, parsed_model = self.validate_scrape_response(response_data)
            
            if not is_valid:
                validation_report["errors"].extend(errors)
            else:
                # Additional validations
                if "query" in response_data:
                    q_valid, q_errors = self.validate_query_structure(response_data["query"])
                    if not q_valid:
                        validation_report["errors"].extend(q_errors)
                
                if "results" in response_data:
                    r_valid, r_errors = self.validate_results_structure(response_data["results"])
                    if not r_valid:
                        validation_report["errors"].extend(r_errors)
                
                if "analytics" in response_data:
                    a_valid, a_errors = self.validate_analytics_structure(response_data["analytics"])
                    if not a_valid:
                        validation_report["errors"].extend(a_errors)
                
                if "execution_metadata" in response_data:
                    e_valid, e_errors = self.validate_execution_metadata(response_data["execution_metadata"])
                    if not e_valid:
                        validation_report["errors"].extend(e_errors)
                    
                    if "stages_timing" in response_data["execution_metadata"]:
                        # Default to expecting database_storage since store_results defaults to True
                        # In practice, this should be determined from the request config
                        s_valid, s_errors = self.validate_stage_timings(
                            response_data["execution_metadata"]["stages_timing"],
                            store_results=True
                        )
                        if not s_valid:
                            validation_report["errors"].extend(s_errors)
        
        elif status == "error":
            # Validate error response
            if "error" not in response_data:
                validation_report["errors"].append("Missing required field: error")
            else:
                e_valid, e_errors = self.validate_error_response(response_data["error"])
                if not e_valid:
                    validation_report["errors"].extend(e_errors)
        
        else:
            validation_report["errors"].append(f"Invalid status: {status}. Expected 'success' or 'error'")
        
        # Calculate compliance
        total_checks = 10  # Approximate number of validation checks
        passed_checks = total_checks - len(validation_report["errors"])
        validation_report["schema_compliance"] = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        # Determine overall status
        if len(validation_report["errors"]) == 0:
            validation_report["overall_status"] = "PASS"
        else:
            validation_report["overall_status"] = "FAIL"
        
        return validation_report
    
    def format_validation_errors(self, errors: List[str]) -> str:
        """Format validation errors for display."""
        if not errors:
            return "No errors"
        
        formatted = []
        for i, error in enumerate(errors, 1):
            formatted.append(f"{i}. {error}")
        
        return "\n".join(formatted)
    
    def generate_example_response(self) -> Dict[str, Any]:
        """Generate example valid response for reference."""
        return {
            "status": "success",
            "timestamp": "2024-01-01T12:00:00Z",
            "request_id": "req_abc123",
            "query": {
                "text": "Best AI agents for coding",
                "category": "ai_tools",
                "confidence_score": 0.95
            },
            "results": {
                "total_items": 15,
                "processed_items": 12,
                "success_rate": 0.80,
                "processed_contents": []
            },
            "analytics": {
                "pages_scraped": 20,
                "processing_time_breakdown": {
                    "query_processing": 1.2,
                    "web_scraping": 28.8,
                    "ai_processing": 14.4,
                    "database_storage": 0.8
                }
            },
            "execution_metadata": {
                "execution_time_ms": 45230.5,
                "stages_timing": {
                    "query_processing": 1.2,
                    "web_scraping": 28.8,
                    "ai_processing": 14.4,
                    "database_storage": 0.8
                }
            }
        }


def load_response_from_file(filepath: str) -> Dict[str, Any]:
    """Load JSON response from file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Response schema validation utility")
    parser.add_argument("--response-file", help="JSON file containing response to validate")
    parser.add_argument("--response-json", help="JSON string to validate")
    parser.add_argument("--schema", choices=["scrape_response", "error_response"], 
                       default="scrape_response", help="Schema to validate against")
    parser.add_argument("--strict", action="store_true", help="Enable strict validation (fail on warnings)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed validation output")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--generate-example", action="store_true", help="Generate example valid response")
    
    args = parser.parse_args()
    
    if args.generate_example:
        validator = ResponseValidator()
        example = validator.generate_example_response()
        print(json.dumps(example, indent=2))
        sys.exit(0)
    
    # Load response data
    if args.response_file:
        response_data = load_response_from_file(args.response_file)
    elif args.response_json:
        try:
            response_data = json.loads(args.response_json)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON string: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Validate response
    validator = ResponseValidator(strict=args.strict)
    
    if args.schema == "scrape_response":
        if response_data.get("status") == "error":
            # Validate as error response
            is_valid, errors = validator.validate_error_response(response_data.get("error", {}))
            validation_report = {
                "overall_status": "PASS" if is_valid else "FAIL",
                "errors": errors,
                "warnings": []
            }
        else:
            # Validate as success response
            validation_report = validator.validate_complete_response(response_data)
    else:
        # Validate error response
        if "error" not in response_data:
            validation_report = {
                "overall_status": "FAIL",
                "errors": ["Missing error field"],
                "warnings": []
            }
        else:
            is_valid, errors = validator.validate_error_response(response_data["error"])
            validation_report = {
                "overall_status": "PASS" if is_valid else "FAIL",
                "errors": errors,
                "warnings": []
            }
    
    # Output results
    if args.json:
        print(json.dumps(validation_report, indent=2))
    else:
        print("="*60)
        print("RESPONSE SCHEMA VALIDATION")
        print("="*60)
        print(f"Overall Status: {validation_report['overall_status']}")
        print(f"Schema Compliance: {validation_report.get('schema_compliance', 0):.1f}%")
        
        if validation_report["errors"]:
            print(f"\nErrors ({len(validation_report['errors'])}):")
            print(validator.format_validation_errors(validation_report["errors"]))
        
        if validation_report.get("warnings"):
            print(f"\nWarnings ({len(validation_report['warnings'])}):")
            print(validator.format_validation_errors(validation_report["warnings"]))
        
        if args.verbose:
            print("\nFull Validation Report:")
            print(json.dumps(validation_report, indent=2))
    
    # Exit with appropriate code
    if validation_report["overall_status"] == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

