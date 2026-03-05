"""OpenUp scraper configuration."""

import os
from typing import Dict
from config.settings import settings


class OpenUpConfig:
    """Configuration for OpenUp scraper."""
    
    BASE_URL = "https://api.openub.com"
    
    @staticmethod
    def get_access_token() -> str:
        """Get OpenUp access token from environment.
        
        여러 가능한 환경 변수명을 시도합니다:
        - OPENUP_ACCESS_TOKEN
        - OPENUB_ACCESS_TOKEN
        - OPENUP_TOKEN
        """
        possible_keys = [
            "OPENUP_ACCESS_TOKEN",
            "OPENUB_ACCESS_TOKEN",
            "OPENUP_TOKEN"
        ]
        
        for key in possible_keys:
            value = os.getenv(key, "")
            if value:
                return value
        
        # 기본값 (문서에서 확인된 토큰)
        # 실제 사용 시 환경 변수로 설정하는 것을 권장
        # 최신 토큰: ff42c207-7967-40fe-89d9-5df14e0de026 ([hash2].txt)
        return os.getenv("OPENUP_ACCESS_TOKEN", "ff42c207-7967-40fe-89d9-5df14e0de026")
    
    @staticmethod
    def get_base_url() -> str:
        """Get OpenUp base URL."""
        return OpenUpConfig.BASE_URL
    
    @staticmethod
    def validate() -> bool:
        """Validate OpenUp configuration."""
        if not OpenUpConfig.get_access_token():
            return False
        return True
