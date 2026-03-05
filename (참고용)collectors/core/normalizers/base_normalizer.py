"""Base normalizer implementation."""

from core.normalizers import BaseNormalizer
from typing import Any, Dict


class DefaultNormalizer(BaseNormalizer):
    """Default normalizer that passes through data with minimal transformation.
    
    This normalizer adds common metadata but doesn't transform the data structure.
    Use this as a fallback or for sources that already match the common schema.
    """
    
    def normalize(self, raw_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize data by adding common metadata.
        
        Args:
            raw_data: Raw data from scraper
            metadata: Optional metadata
            
        Returns:
            Normalized data with common metadata
        """
        normalized = {
            'metadata': self._get_common_metadata(metadata),
            'data': raw_data
        }
        
        return normalized

