"""API Keys configuration management."""

import os
from typing import Optional


class APIKeys:
    """Manages API keys for various services."""
    
    @staticmethod
    def get_vworld_key() -> str:
        """Get VWorld API key."""
        return os.getenv("VWORLD_API_KEY", "")
    
    @staticmethod
    def get_kakao_key() -> str:
        """Get Kakao API key."""
        return os.getenv("KAKAO_API_KEY", "")
    
    @staticmethod
    def get_mapbox_token() -> str:
        """Get Mapbox token."""
        return os.getenv("MAPBOX_TOKEN", "")
    
    @staticmethod
    def get_ors_key() -> str:
        """Get OpenRouteService API key."""
        return os.getenv("ORS_API_KEY", "")
    
    @staticmethod
    def validate_vworld() -> bool:
        """Validate VWorld API key."""
        return bool(APIKeys.get_vworld_key())
    
    @staticmethod
    def validate_kakao() -> bool:
        """Validate Kakao API key."""
        return bool(APIKeys.get_kakao_key())
    
    @staticmethod
    def validate_mapbox() -> bool:
        """Validate Mapbox token."""
        return bool(APIKeys.get_mapbox_token())
    
    @staticmethod
    def validate_ors() -> bool:
        """Validate OpenRouteService API key."""
        return bool(APIKeys.get_ors_key())

