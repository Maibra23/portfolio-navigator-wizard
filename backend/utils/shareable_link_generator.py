#!/usr/bin/env python3
"""
Shareable Link Generator
Generates secure shareable links for portfolio data with expiry and password protection
"""

import logging
import json
import hashlib
import secrets
from typing import Dict, Optional
from datetime import datetime, timedelta
import redis

logger = logging.getLogger(__name__)


class ShareableLinkGenerator:
    """
    Generates and manages shareable links for portfolio data
    Uses Redis for storage with TTL for automatic expiry
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize the shareable link generator
        
        Args:
            redis_client: Redis client instance (optional, will create if not provided)
        """
        if redis_client is None:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("✅ Redis connection established for shareable links")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}")
                self.redis_client = None
        else:
            self.redis_client = redis_client
        
        self.link_prefix = "shareable_link:"
        self.password_prefix = "shareable_password:"
    
    def _generate_link_id(self) -> str:
        """Generate a unique link ID"""
        return secrets.token_urlsafe(16)
    
    def _hash_password(self, password: str) -> str:
        """Hash a password for storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return self._hash_password(password) == hashed
    
    def generate_link(self, portfolio_data: Dict, 
                     expiry_days: int = 30,
                     password: Optional[str] = None) -> str:
        """
        Generate a secure shareable link
        
        Args:
            portfolio_data: Portfolio data to share
            expiry_days: Number of days until link expires (default: 30)
            password: Optional password for link protection
            
        Returns:
            Link ID (to be used in URL)
        """
        if self.redis_client is None:
            raise RuntimeError("Redis client not available. Cannot generate shareable links.")
        
        # Generate unique link ID
        link_id = self._generate_link_id()
        
        # Prepare data for storage
        link_data = {
            "portfolio_data": portfolio_data,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=expiry_days)).isoformat(),
            "has_password": password is not None
        }
        
        # Store link data in Redis with TTL
        redis_key = f"{self.link_prefix}{link_id}"
        ttl_seconds = expiry_days * 24 * 60 * 60  # Convert days to seconds
        
        self.redis_client.setex(
            redis_key,
            ttl_seconds,
            json.dumps(link_data)
        )
        
        # Store password hash if provided
        if password:
            password_key = f"{self.password_prefix}{link_id}"
            password_hash = self._hash_password(password)
            self.redis_client.setex(
                password_key,
                ttl_seconds,
                password_hash
            )
        
        logger.info(f"Generated shareable link: {link_id} (expires in {expiry_days} days)")
        return link_id
    
    def get_link_data(self, link_id: str, password: Optional[str] = None) -> Dict:
        """
        Retrieve data from a shareable link
        
        Args:
            link_id: The link ID
            password: Optional password if link is protected
            
        Returns:
            Dictionary containing portfolio data and metadata
            
        Raises:
            ValueError: If link is invalid, expired, or password is incorrect
        """
        if self.redis_client is None:
            raise RuntimeError("Redis client not available. Cannot retrieve shareable links.")
        
        # Check if link exists
        redis_key = f"{self.link_prefix}{link_id}"
        link_data_str = self.redis_client.get(redis_key)
        
        if not link_data_str:
            raise ValueError("Link not found or expired")
        
        # Parse link data
        link_data = json.loads(link_data_str)
        
        # Check password if required
        if link_data.get("has_password", False):
            if not password:
                raise ValueError("Password required for this link")
            
            password_key = f"{self.password_prefix}{link_id}"
            stored_hash = self.redis_client.get(password_key)
            
            if not stored_hash or not self._verify_password(password, stored_hash):
                raise ValueError("Incorrect password")
        
        return link_data
    
    def validate_link(self, link_id: str) -> bool:
        """
        Check if a link is valid and not expired
        
        Args:
            link_id: The link ID to validate
            
        Returns:
            True if link is valid, False otherwise
        """
        if self.redis_client is None:
            return False
        
        try:
            redis_key = f"{self.link_prefix}{link_id}"
            link_data_str = self.redis_client.get(redis_key)
            
            if not link_data_str:
                return False
            
            # Link exists and hasn't expired (Redis TTL handles expiry)
            return True
        
        except Exception as e:
            logger.error(f"Error validating link {link_id}: {e}")
            return False
    
    def delete_link(self, link_id: str) -> bool:
        """
        Delete a shareable link (manual deletion before expiry)
        
        Args:
            link_id: The link ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if self.redis_client is None:
            return False
        
        try:
            redis_key = f"{self.link_prefix}{link_id}"
            password_key = f"{self.password_prefix}{link_id}"
            
            deleted = bool(self.redis_client.delete(redis_key))
            self.redis_client.delete(password_key)  # Also delete password if exists
            
            if deleted:
                logger.info(f"Deleted shareable link: {link_id}")
            
            return deleted
        
        except Exception as e:
            logger.error(f"Error deleting link {link_id}: {e}")
            return False
    
    def get_link_info(self, link_id: str) -> Optional[Dict]:
        """
        Get link metadata without requiring password
        
        Args:
            link_id: The link ID
            
        Returns:
            Dictionary with link metadata (without portfolio data) or None if not found
        """
        if self.redis_client is None:
            return None
        
        try:
            redis_key = f"{self.link_prefix}{link_id}"
            link_data_str = self.redis_client.get(redis_key)
            
            if not link_data_str:
                return None
            
            link_data = json.loads(link_data_str)
            
            # Return metadata only (no portfolio data)
            return {
                "link_id": link_id,
                "created_at": link_data.get("created_at"),
                "expires_at": link_data.get("expires_at"),
                "has_password": link_data.get("has_password", False),
                "is_valid": True
            }
        
        except Exception as e:
            logger.error(f"Error getting link info for {link_id}: {e}")
            return None
