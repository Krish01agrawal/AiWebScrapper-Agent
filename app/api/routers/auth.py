"""
API key management endpoints for authentication.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.auth import APIKeyManager, get_api_key_manager, require_permission, APIKey
from app.api.schemas import APIResponse, ErrorDetail, ErrorResponse
from app.utils.response import format_success_response, format_error_response
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class CreateAPIKeyRequest(BaseModel):
    """Request model for creating API keys."""
    name: str = Field(..., description="Human-readable name for the API key")
    permissions: List[str] = Field(
        default=["read", "scrape"], 
        description="List of permissions for the API key"
    )
    rate_limit: int = Field(
        default=120, 
        ge=1, 
        le=10000, 
        description="Rate limit in requests per minute"
    )
    expires_in_days: Optional[int] = Field(
        None, 
        ge=1, 
        le=365, 
        description="Expiration time in days (optional)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Production API Key",
                "permissions": ["read", "scrape"],
                "rate_limit": 500,
                "expires_in_days": 90
            }
        }
    }


class APIKeyResponse(BaseModel):
    """Response model for API key information."""
    key_id: str = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="Human-readable name")
    api_key: str = Field(..., description="The actual API key (only shown on creation)")
    permissions: List[str] = Field(..., description="List of permissions")
    rate_limit: int = Field(..., description="Rate limit in requests per minute")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(..., description="Whether the key is active")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "key_id": "abc123def456",
                "name": "Production API Key",
                "api_key": "traycer_xyz789...",
                "permissions": ["read", "scrape"],
                "rate_limit": 500,
                "created_at": "2024-01-01T12:00:00Z",
                "expires_at": "2024-04-01T12:00:00Z",
                "is_active": True
            }
        }
    }


class APIKeyInfo(BaseModel):
    """API key information without the actual key."""
    key_id: str = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="Human-readable name")
    permissions: List[str] = Field(..., description="List of permissions")
    rate_limit: int = Field(..., description="Rate limit in requests per minute")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(..., description="Whether the key is active")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(..., description="Total usage count")


class VerifyAPIKeyResponse(BaseModel):
    """Response model for API key verification."""
    valid: bool = Field(..., description="Whether the API key is valid")
    key_info: Optional[APIKeyInfo] = Field(None, description="API key information if valid")
    message: str = Field(..., description="Verification message")


@router.post(
    "/keys",
    response_model=APIKeyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    http_request: Request,
    current_api_key: APIKey = Depends(require_permission("admin"))
) -> APIKeyResponse:
    """
    Create a new API key.
    
    Requires admin permission. The API key will be returned only once.
    
    Args:
        request: API key creation request
        http_request: FastAPI request object
        current_api_key: Current authenticated API key (must have admin permission)
        
    Returns:
        Created API key with full details
        
    Raises:
        HTTPException: For validation errors or permission issues
    """
    settings = get_settings()
    
    try:
        # Get API key manager
        api_key_manager = get_api_key_manager()
        if not api_key_manager:
            raise HTTPException(
                status_code=503,
                detail="API key management service unavailable"
            )
        
        # Generate new API key
        api_key = api_key_manager.generate_key(
            name=request.name,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            expires_in_days=request.expires_in_days
        )
        
        # Get the API key object for response
        api_key_obj = api_key_manager.validate_key(api_key)
        if not api_key_obj:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve created API key"
            )
        
        logger.info(
            f"API key created: {request.name} by {current_api_key.key_id} "
            f"from {http_request.client.host if http_request.client else 'unknown'}"
        )
        
        return APIKeyResponse(
            key_id=api_key_obj.key_id,
            name=api_key_obj.name,
            api_key=api_key,
            permissions=api_key_obj.permissions,
            rate_limit=api_key_obj.rate_limit,
            created_at=api_key_obj.created_at,
            expires_at=api_key_obj.expires_at,
            is_active=api_key_obj.is_active
        )
        
    except Exception as e:
        logger.error(f"Failed to create API key: {e}", exc_info=True)
        
        error_detail = ErrorDetail(
            error_code="API_KEY_CREATION_FAILED",
            message="Failed to create API key",
            context={"error": str(e)} if getattr(settings, 'api_enable_detailed_errors', True) else None,
            recovery_suggestions=[
                "Check your permissions",
                "Verify the request parameters",
                "Try again later"
            ]
        )
        
        error_response = format_error_response(
            error_code="API_KEY_CREATION_FAILED",
            message="API key creation failed",
            details=[error_detail],
            status_code=500
        )
        
        return JSONResponse(content=error_response, status_code=500)


@router.get(
    "/keys",
    response_model=List[APIKeyInfo],
    responses={
        403: {"model": ErrorResponse, "description": "Permission denied"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_api_keys(
    current_api_key: APIKey = Depends(require_permission("admin"))
) -> List[APIKeyInfo]:
    """
    List all API keys.
    
    Requires admin permission. Returns key information without the actual keys.
    
    Args:
        current_api_key: Current authenticated API key (must have admin permission)
        
    Returns:
        List of API key information
        
    Raises:
        HTTPException: For permission issues
    """
    try:
        # Get API key manager
        api_key_manager = get_api_key_manager()
        if not api_key_manager:
            raise HTTPException(
                status_code=503,
                detail="API key management service unavailable"
            )
        
        # Get all keys
        keys_info = api_key_manager.list_keys()
        
        # Convert to response format
        api_keys = []
        for key_info in keys_info:
            api_keys.append(APIKeyInfo(**key_info))
        
        logger.info(f"API keys listed by {current_api_key.key_id}")
        
        return api_keys
        
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}", exc_info=True)
        
        error_detail = ErrorDetail(
            error_code="API_KEY_LIST_FAILED",
            message="Failed to list API keys",
            recovery_suggestions=[
                "Check your permissions",
                "Try again later"
            ]
        )
        
        error_response = format_error_response(
            error_code="API_KEY_LIST_FAILED",
            message="API key listing failed",
            details=[error_detail],
            status_code=500
        )
        
        return JSONResponse(content=error_response, status_code=500)


@router.delete(
    "/keys/{key_id}",
    responses={
        200: {"description": "API key revoked successfully"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "API key not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def revoke_api_key(
    key_id: str,
    current_api_key: APIKey = Depends(require_permission("admin"))
) -> Dict[str, Any]:
    """
    Revoke an API key.
    
    Requires admin permission. The key will be immediately invalidated.
    
    Args:
        key_id: ID of the API key to revoke
        current_api_key: Current authenticated API key (must have admin permission)
        
    Returns:
        Success message
        
    Raises:
        HTTPException: For permission issues or if key not found
    """
    try:
        # Get API key manager
        api_key_manager = get_api_key_manager()
        if not api_key_manager:
            raise HTTPException(
                status_code=503,
                detail="API key management service unavailable"
            )
        
        # Revoke the key
        success = api_key_manager.revoke_key(key_id)
        
        if not success:
            error_detail = ErrorDetail(
                error_code="API_KEY_NOT_FOUND",
                message=f"API key with ID {key_id} not found",
                recovery_suggestions=[
                    "Check the key ID",
                    "Verify the key exists"
                ]
            )
            
            error_response = format_error_response(
                error_code="API_KEY_NOT_FOUND",
                message="API key not found",
                details=[error_detail],
                status_code=404
            )
            
            return JSONResponse(content=error_response, status_code=404)
        
        logger.info(f"API key {key_id} revoked by {current_api_key.key_id}")
        
        return format_success_response(
            message="API key revoked successfully",
            data={"key_id": key_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to revoke API key {key_id}: {e}", exc_info=True)
        
        error_detail = ErrorDetail(
            error_code="API_KEY_REVOKE_FAILED",
            message="Failed to revoke API key",
            recovery_suggestions=[
                "Check your permissions",
                "Try again later"
            ]
        )
        
        error_response = format_error_response(
            error_code="API_KEY_REVOKE_FAILED",
            message="API key revocation failed",
            details=[error_detail],
            status_code=500
        )
        
        return JSONResponse(content=error_response, status_code=500)


@router.post(
    "/verify",
    response_model=VerifyAPIKeyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def verify_api_key(
    current_api_key: Optional[APIKey] = Depends(require_permission("read"))
) -> VerifyAPIKeyResponse:
    """
    Verify the current API key.
    
    This endpoint validates the provided API key and returns information about it.
    
    Args:
        current_api_key: Current authenticated API key
        
    Returns:
        Verification result with key information
        
    Raises:
        HTTPException: For invalid API key
    """
    try:
        if not current_api_key:
            return VerifyAPIKeyResponse(
                valid=False,
                key_info=None,
                message="No API key provided"
            )
        
        # Get API key manager for additional info
        api_key_manager = get_api_key_manager()
        if api_key_manager:
            # Get fresh key info
            keys_info = api_key_manager.list_keys()
            key_info = next(
                (k for k in keys_info if k["key_id"] == current_api_key.key_id), 
                None
            )
            
            if key_info:
                return VerifyAPIKeyResponse(
                    valid=True,
                    key_info=APIKeyInfo(**key_info),
                    message="API key is valid"
                )
        
        # Fallback to basic info
        return VerifyAPIKeyResponse(
            valid=True,
            key_info=APIKeyInfo(
                key_id=current_api_key.key_id,
                name=current_api_key.name,
                permissions=current_api_key.permissions,
                rate_limit=current_api_key.rate_limit,
                created_at=current_api_key.created_at,
                expires_at=current_api_key.expires_at,
                is_active=current_api_key.is_active,
                last_used=current_api_key.last_used,
                usage_count=current_api_key.usage_count
            ),
            message="API key is valid"
        )
        
    except Exception as e:
        logger.error(f"Failed to verify API key: {e}", exc_info=True)
        
        error_detail = ErrorDetail(
            error_code="API_KEY_VERIFY_FAILED",
            message="Failed to verify API key",
            recovery_suggestions=[
                "Check your API key",
                "Try again later"
            ]
        )
        
        error_response = format_error_response(
            error_code="API_KEY_VERIFY_FAILED",
            message="API key verification failed",
            details=[error_detail],
            status_code=500
        )
        
        return JSONResponse(content=error_response, status_code=500)


@router.get(
    "/permissions",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Available permissions list"}
    }
)
async def get_permissions() -> Dict[str, Any]:
    """
    Get available permissions for API keys.
    
    Returns a list of available permissions and their descriptions.
    
    Returns:
        Dictionary with available permissions and descriptions
    """
    permissions = {
        "read": "Read access to API endpoints",
        "scrape": "Access to web scraping functionality",
        "admin": "Administrative access including key management",
        "metrics": "Access to metrics and analytics endpoints"
    }
    
    return format_success_response(
        message="Available permissions",
        data={
            "permissions": permissions,
            "default_permissions": ["read", "scrape"],
            "admin_permissions": ["admin"]
        }
    )
