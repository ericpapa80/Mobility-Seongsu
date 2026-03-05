"""SBIZ scraper configuration."""

import os
from typing import Dict
from config.settings import settings


class SBIZConfig:
    """Configuration for SBIZ scraper."""
    
    @staticmethod
    def get_service_key() -> str:
        """Get SBIZ service key from environment.
        
        여러 가능한 환경 변수명을 시도합니다:
        - SBIZ_SERVICE_KEY
        - DATA_GO_KR_SERVICE_KEY
        - PUBLICDATA_SERVICE_KEY
        - SERVICE_KEY (공공데이터포털 일반)
        """
        # 여러 가능한 변수명 시도
        possible_keys = [
            "SBIZ_SERVICE_KEY",
            "DATA_GO_KR_SERVICE_KEY", 
            "PUBLICDATA_SERVICE_KEY",
            "SERVICE_KEY"
        ]
        
        for key in possible_keys:
            value = os.getenv(key, "")
            if value:
                return value
        
        return ""
    
    @staticmethod
    def get_base_url() -> str:
        """Get SBIZ base URL."""
        return "http://apis.data.go.kr/B553077/api/open/sdsc2"
    
    @staticmethod
    def validate() -> bool:
        """Validate SBIZ configuration."""
        if not SBIZConfig.get_service_key():
            return False
        return True

