"""SGIS scraper configuration."""

import os
from typing import Dict
from config.settings import settings


class SGISConfig:
    """Configuration for SGIS scraper."""
    
    @staticmethod
    def get_base_url() -> str:
        """Get SGIS base URL."""
        return os.getenv("SGIS_BASE_URL", "https://sgis.mods.go.kr")
    
    @staticmethod
    def get_consumer_key() -> str:
        """Get SGIS consumer key."""
        return os.getenv("SGIS_CONSUMER_KEY", "")
    
    @staticmethod
    def get_consumer_secret() -> str:
        """Get SGIS consumer secret."""
        return os.getenv("SGIS_CONSUMER_SECRET", "")
    
    @staticmethod
    def get_credentials() -> Dict[str, str]:
        """Get SGIS credentials as dictionary."""
        return {
            'consumer_key': SGISConfig.get_consumer_key(),
            'consumer_secret': SGISConfig.get_consumer_secret()
        }
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get SGIS request headers."""
        base_url = SGISConfig.get_base_url()
        return {
            'Accept': '*/*',
            'Accept-Language': 'ko,en;q=0.9,en-US;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': base_url,
            'Pragma': 'no-cache',
            'Referer': f'{base_url}/view/technicalBiz/technicalBizMap?tec=0',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    
    @staticmethod
    def validate() -> bool:
        """Validate SGIS configuration."""
        if not SGISConfig.get_consumer_key():
            return False
        if not SGISConfig.get_consumer_secret():
            return False
        return True

