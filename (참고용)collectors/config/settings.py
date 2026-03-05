"""Settings and configuration management."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Settings:
    """Application settings manager."""
    
    def __init__(self, env_file: Optional[Path] = None):
        """Initialize settings.
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env"
        
        # Load environment variables
        if env_file.exists():
            load_dotenv(env_file)
        else:
            load_dotenv()  # Try default .env location
        
        # Base paths
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        
        # SGIS settings
        self.sgis_base_url = os.getenv("SGIS_BASE_URL", "https://sgis.mods.go.kr")
        self.sgis_consumer_key = os.getenv("SGIS_CONSUMER_KEY", "")
        self.sgis_consumer_secret = os.getenv("SGIS_CONSUMER_SECRET", "")
        
        # API Keys
        self.vworld_api_key = os.getenv("VWORLD_API_KEY", "")
        self.kakao_api_key = os.getenv("KAKAO_API_KEY", "")
        self.mapbox_token = os.getenv("MAPBOX_TOKEN", "")
        self.ors_api_key = os.getenv("ORS_API_KEY", "")
        
        # Database settings
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_name = os.getenv("DB_NAME", "")
        self.db_user = os.getenv("DB_USER", "")
        self.db_password = os.getenv("DB_PASSWORD", "")
        
        # API settings
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "1"))
    
    def validate_sgis_settings(self) -> bool:
        """Validate SGIS-related settings.
        
        Returns:
            True if all required settings are present
        """
        if not self.sgis_consumer_key:
            return False
        if not self.sgis_consumer_secret:
            return False
        return True
    
    def get_database_url(self) -> str:
        """Get database connection URL.
        
        Returns:
            Database connection URL string
        """
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def get_sgis_headers(self) -> dict:
        """Get SGIS request headers.
        
        Returns:
            Dictionary of headers
        """
        return {
            'Accept': '*/*',
            'Accept-Language': 'ko,en;q=0.9,en-US;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.sgis_base_url,
            'Pragma': 'no-cache',
            'Referer': f'{self.sgis_base_url}/view/technicalBiz/technicalBizMap?tec=0',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }


# Global settings instance
settings = Settings()

