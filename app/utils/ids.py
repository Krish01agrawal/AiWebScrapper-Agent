import hashlib
from typing import Optional


def generate_content_id(url: str, title: Optional[str] = None) -> str:
    """
    Generate a consistent content ID based on URL and title.
    
    Args:
        url: The content URL
        title: Optional content title
        
    Returns:
        MD5 hash of the combined URL and title
    """
    combined = f"{url}|{title or 'no-title'}"
    return hashlib.md5(combined.encode('utf-8')).hexdigest()
