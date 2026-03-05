"""SGIS data normalizer for converting raw SGIS data to common schema."""

import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.normalizers import BaseNormalizer
from core.logger import get_logger

logger = get_logger(__name__)


class SGISNormalizer(BaseNormalizer):
    """Normalizer for SGIS technical business map data.
    
    Converts SGIS API response to common schema format.
    """
    
    def __init__(self):
        """Initialize SGIS normalizer."""
        super().__init__(source_name="sgis")
    
    def normalize(self, raw_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize SGIS data to common schema.
        
        Args:
            raw_data: Raw SGIS API response
            metadata: Optional metadata (theme_cd, year, adm_cd, etc.)
            
        Returns:
            Normalized data in common schema format
        """
        # Extract result items
        items = raw_data.get('result', [])
        
        # Normalize each item
        normalized_items = []
        for item in items:
            normalized_item = {
                'id': item.get('sufid', ''),
                'name': item.get('corp_nm', ''),
                'address': item.get('naddr', ''),
                'coordinates': {
                    'x': item.get('x', ''),
                    'y': item.get('y', ''),
                    'x_5179': item.get('x_5179', ''),
                    'y_5179': item.get('y_5179', ''),
                    'lon': item.get('lon', ''),
                    'lat': item.get('lat', '')
                },
                'administrative_code': item.get('adm_cd', ''),
                'theme_code': item.get('theme_cd', ''),
                'weight': item.get('wgt', 1),
                'raw': item  # Keep original data for reference
            }
            normalized_items.append(normalized_item)
        
        # Build normalized structure
        normalized = {
            'metadata': self._get_common_metadata(metadata),
            'source_specific': {
                'theme_cd': metadata.get('theme_cd') if metadata else None,
                'year': metadata.get('year') if metadata else None,
                'adm_cd': metadata.get('adm_cd') if metadata else None,
                'data_type': metadata.get('data_type') if metadata else None,
            },
            'data': {
                'items': normalized_items,
                'count': len(normalized_items)
            }
        }
        
        logger.info(f"Normalized {len(normalized_items)} SGIS items")
        
        return normalized

