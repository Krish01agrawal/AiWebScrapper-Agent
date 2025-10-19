"""
API key authentication system with support for multiple keys, rate limiting per key, and key management.
"""

import secrets
import hashlib
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

from app.core.config import settings


@dataclass
class APIKey:
    """API Key model with permissions and metadata."""
    key_id: str
    key_hash: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    rate_limit: int = 120  # requests per minute
    permissions: List[str] = field(default_factory=list)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    
    def is_valid(self) -> bool:
        """Check if key is active and not expired."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def check_permission(self, permission: str) -> bool:
        """Check if key has required permission."""
        return permission in self.permissions or "admin" in self.permissions
    
    def record_usage(self):
        """Record key usage."""
        self.last_used = datetime.utcnow()
        self.usage_count += 1


class APIKeyManager:
    """Manager for API keys with validation and rate limiting."""
    
    def __init__(self):
        """Initialize API key manager."""
        self.keys: Dict[str, APIKey] = {}
        self.rate_limits: Dict[str, List[float]] = {}  # key_id -> timestamps
        self.logger = logging.getLogger(__name__)
    
    def generate_key(
        self,
        name: str,
        permissions: List[str],
        rate_limit: int = 120,
        expires_in_days: Optional[int] = None
    ) -> str:
        """Generate new API key."""
        # Generate secure random key
        random_part = secrets.token_urlsafe(32)
        api_key = f"traycer_{random_part}"
        
        # Create hash for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_id = hashlib.md5(key_hash.encode()).hexdigest()[:16]
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create API key object
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            rate_limit=rate_limit,
            permissions=permissions
        )
        
        # Store by hash
        self.keys[key_hash] = api_key_obj
        
        self.logger.info(f"Generated new API key: {name} ({key_id})")
        return api_key
    
    def validate_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key and return APIKey object."""
        if not api_key.startswith("traycer_"):
            return None
        
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash not in self.keys:
            return None
        
        api_key_obj = self.keys[key_hash]
        if not api_key_obj.is_valid():
            return None
        
        return api_key_obj
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke API key by ID."""
        for key_hash, api_key_obj in self.keys.items():
            if api_key_obj.key_id == key_id:
                api_key_obj.is_active = False
                self.logger.info(f"Revoked API key: {api_key_obj.name} ({key_id})")
                return True
        return False
    
    def list_keys(self) -> List[Dict[str, Any]]:
        """List all keys (without sensitive data)."""
        keys_info = []
        for api_key_obj in self.keys.values():
            keys_info.append({
                "key_id": api_key_obj.key_id,
                "name": api_key_obj.name,
                "created_at": api_key_obj.created_at.isoformat(),
                "expires_at": api_key_obj.expires_at.isoformat() if api_key_obj.expires_at else None,
                "is_active": api_key_obj.is_active,
                "rate_limit": api_key_obj.rate_limit,
                "permissions": api_key_obj.permissions,
                "last_used": api_key_obj.last_used.isoformat() if api_key_obj.last_used else None,
                "usage_count": api_key_obj.usage_count
            })
        return keys_info
    
    def load_keys_from_env(self) -> int:
        """Load predefined keys from environment variables."""
        if not settings.api_keys:
            return 0
        
        loaded_count = 0
        key_entries = settings.api_keys.split(',')
        
        for entry in key_entries:
            entry = entry.strip()
            if not entry:
                continue
            
            try:
                # Parse format: key:name:permissions
                parts = entry.split(':')
                if len(parts) < 2:
                    continue
                
                api_key = parts[0]
                name = parts[1]
                permissions = parts[2].split(',') if len(parts) > 2 else []
                
                # Validate key format
                if not api_key.startswith("traycer_"):
                    continue
                
                # Hash the key
                key_hash = hashlib.sha256(api_key.encode()).hexdigest()
                key_id = hashlib.md5(key_hash.encode()).hexdigest()[:16]
                
                # Create API key object
                api_key_obj = APIKey(
                    key_id=key_id,
                    key_hash=key_hash,
                    name=name,
                    created_at=datetime.utcnow(),
                    rate_limit=settings.api_key_rate_limit_per_minute,
                    permissions=permissions
                )
                
                self.keys[key_hash] = api_key_obj
                loaded_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to load API key from env: {e}")
                continue
        
        self.logger.info(f"Loaded {loaded_count} API keys from environment")
        return loaded_count
    
    def check_rate_limit(self, key_id: str) -> bool:
        """Check if key has exceeded rate limit."""
        now = time.time()
        minute_ago = now - 60
        
        # Get or create rate limit tracking
        if key_id not in self.rate_limits:
            self.rate_limits[key_id] = []
        
        # Clean old timestamps
        self.rate_limits[key_id] = [
            timestamp for timestamp in self.rate_limits[key_id]
            if timestamp > minute_ago
        ]
        
        # Get API key rate limit
        api_key_obj = None
        for key_obj in self.keys.values():
            if key_obj.key_id == key_id:
                api_key_obj = key_obj
                break
        
        if not api_key_obj:
            return False
        
        # Check if under limit
        return len(self.rate_limits[key_id]) < api_key_obj.rate_limit
    
    def record_request(self, key_id: str) -> None:
        """Record request timestamp for rate limiting."""
        now = time.time()
        
        if key_id not in self.rate_limits:
            self.rate_limits[key_id] = []
        
        self.rate_limits[key_id].append(now)
        
        # Update usage stats
        for api_key_obj in self.keys.values():
            if api_key_obj.key_id == key_id:
                api_key_obj.record_usage()
                break


# Security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[APIKey]:
    """FastAPI dependency for API key verification."""
    if not api_key:
        return None
    
    # Get manager from global state (will be set in main.py)
    manager = get_api_key_manager()
    if not manager:
        return None
    
    api_key_obj = manager.validate_key(api_key)
    if not api_key_obj:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    # Record request (rate limiting handled by middleware)
    manager.record_request(api_key_obj.key_id)
    
    return api_key_obj


async def optional_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[APIKey]:
    """Optional API key verification (allows unauthenticated access)."""
    if not api_key:
        return None
    
    return await verify_api_key(api_key)


def require_permission(permission: str):
    """Create dependency that requires specific permission."""
    async def check_permission(api_key: Optional[APIKey] = Depends(verify_api_key)):
        if not api_key:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not api_key.check_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required"
            )
        
        return api_key
    
    return check_permission


# Global manager instance
_manager_instance: Optional[APIKeyManager] = None


def get_api_key_manager() -> Optional[APIKeyManager]:
    """Get global API key manager instance."""
    return _manager_instance


def initialize_api_key_manager() -> APIKeyManager:
    """Initialize global API key manager."""
    global _manager_instance
    _manager_instance = APIKeyManager()
    return _manager_instance


# Import logging at the end to avoid circular imports
import logging
