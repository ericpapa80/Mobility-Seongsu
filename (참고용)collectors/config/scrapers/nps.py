"""NPS scraper configuration."""

import os
from pathlib import Path
from typing import Dict
from config.settings import settings


class NPSConfig:
    """Configuration for NPS scraper."""
    
    @staticmethod
    def get_default_csv_path() -> str:
        """Get default NPS CSV file path.
        
        Returns:
            Path to default NPS CSV file
        """
        # Check environment variable first
        csv_path = os.getenv("NPS_CSV_PATH", "")
        if csv_path and Path(csv_path).exists():
            return csv_path
        
        # Default to docs/sources/nps directory
        project_root = Path(__file__).parent.parent.parent
        default_path = project_root / "docs" / "sources" / "nps" / "국민연금공단_국민연금 가입 사업장 내역_20251124.csv"
        
        return str(default_path)
    
    @staticmethod
    def get_data_directory() -> str:
        """Get NPS data directory path.
        
        Returns:
            Path to NPS data directory
        """
        project_root = Path(__file__).parent.parent.parent
        return str(project_root / "docs" / "sources" / "nps")
    
    @staticmethod
    def validate() -> bool:
        """Validate NPS configuration.
        
        Returns:
            True if configuration is valid
        """
        csv_path = NPSConfig.get_default_csv_path()
        if not csv_path or not Path(csv_path).exists():
            return False
        return True

