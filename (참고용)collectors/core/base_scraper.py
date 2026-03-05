"""Base scraper class for all scrapers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import json
from datetime import datetime


class BaseScraper(ABC):
    """Base class for all scrapers.
    
    This class provides common functionality for all scrapers including
    data validation, saving, and error handling.
    """
    
    def __init__(self, name: str, output_dir: Optional[Path] = None):
        """Initialize base scraper.
        
        Args:
            name: Name of the scraper (e.g., 'sgis')
            output_dir: Base output directory for saving data
        """
        self.name = name
        self.output_dir = output_dir or Path("data")
        self.raw_dir = self.output_dir / "raw" / self.name
        self.processed_dir = self.output_dir / "processed" / self.name
        
        # Create output directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def scrape(self, **kwargs) -> Dict[str, Any]:
        """Scrape data from the source.
        
        This method must be implemented by each scraper.
        
        Args:
            **kwargs: Scraper-specific parameters
            
        Returns:
            Dictionary containing scraped data
        """
        pass
    
    def fetch(self, **kwargs) -> Dict[str, Any]:
        """Fetch data using the scrape method.
        
        Args:
            **kwargs: Parameters to pass to scrape method
            
        Returns:
            Dictionary containing fetched data
        """
        return self.scrape(**kwargs)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate scraped data.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
        if not data:
            return False
        return True
    
    def save_raw(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save raw data to file.
        
        Args:
            data: Data to save
            filename: Optional filename (if not provided, uses timestamp)
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_dir = self.raw_dir / timestamp
        timestamp_dir.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            filename = f"{self.name}_raw_{timestamp}.json"
        
        filepath = timestamp_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def save_processed(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save processed data to file.
        
        Args:
            data: Data to save
            filename: Optional filename (if not provided, uses timestamp)
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_dir = self.processed_dir / timestamp
        timestamp_dir.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            filename = f"{self.name}_processed_{timestamp}.json"
        
        filepath = timestamp_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def save(self, data: Dict[str, Any], save_raw: bool = True, save_processed: bool = False) -> Dict[str, Path]:
        """Save data in both raw and/or processed formats.
        
        Args:
            data: Data to save
            save_raw: Whether to save raw data
            save_processed: Whether to save processed data
            
        Returns:
            Dictionary with 'raw' and/or 'processed' keys containing file paths
        """
        result = {}
        
        if not self.validate(data):
            raise ValueError("Invalid data format")
        
        if save_raw:
            result['raw'] = self.save_raw(data)
        
        if save_processed:
            result['processed'] = self.save_processed(data)
        
        return result

