"""Data normalizers for converting raw data to common schema."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from datetime import datetime


class BaseNormalizer(ABC):
    """Base class for all data normalizers.
    
    Normalizers convert raw scraped data into a common schema format
    for downstream processing and analysis.
    """
    
    def __init__(self, source_name: str):
        """Initialize normalizer.
        
        Args:
            source_name: Name of the data source (e.g., 'sgis', 'naver_reviews')
        """
        self.source_name = source_name
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize raw data to common schema.
        
        Args:
            raw_data: Raw data from scraper
            metadata: Optional metadata (timestamp, batch_id, etc.)
            
        Returns:
            Normalized data in common schema format
        """
        pass
    
    def _get_common_metadata(self, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get common metadata fields.
        
        Args:
            metadata: Optional metadata to merge
            
        Returns:
            Common metadata dictionary
        """
        common_meta = {
            'source': self.source_name,
            'collected_at': datetime.now().isoformat(),
            'normalized_at': datetime.now().isoformat(),
        }
        
        if metadata:
            common_meta.update(metadata)
        
        return common_meta

