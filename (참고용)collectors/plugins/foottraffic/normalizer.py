"""Foottraffic data normalizer for converting raw data to common schema."""

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.normalizers import BaseNormalizer
from core.logger import get_logger

logger = get_logger(__name__)


class FoottrafficNormalizer(BaseNormalizer):
    """Normalizer for 골목길 유동인구 data.
    
    Converts 골목길 유동인구 API response to common schema format.
    """
    
    def __init__(self):
        """Initialize Foottraffic normalizer."""
        super().__init__(source_name="foottraffic")
    
    def normalize(self, raw_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize 골목길 유동인구 data to common schema.
        
        Args:
            raw_data: Raw API response (should contain 'records' list)
            metadata: Optional metadata (bounds, dayweek, agrde, tmzon, etc.)
            
        Returns:
            Normalized data in common schema format
        """
        # Extract records from raw_data
        records = raw_data.get('records', [])
        
        if not records:
            logger.warning("No records found in raw data")
            records = []
        
        # Normalize each record
        normalized_items = []
        for record in records:
            normalized_item = {
                'road_link_id': record.get('roadLinkId', ''),
                'cost': record.get('cost', 0),
                'grade': record.get('grade', 0),
                'percentage': record.get('per', 0),
                'max_cost': record.get('mxcost', 0),
                'min_cost': record.get('micost', 0),
                'avg_cost': record.get('acost', 0),
                'geometry': {
                    'wkt': record.get('wkt', ''),
                    'type': 'LINESTRING' if 'LINESTRING' in record.get('wkt', '') else 'UNKNOWN'
                },
                'raw': record  # Keep original data for reference
            }
            normalized_items.append(normalized_item)
        
        # Build normalized structure
        normalized = {
            'metadata': self._get_common_metadata(metadata),
            'source_specific': {
                'bounds': metadata.get('bounds') if metadata else None,
                'dayweek': metadata.get('dayweek') if metadata else None,
                'agrde': metadata.get('agrde') if metadata else None,
                'tmzon': metadata.get('tmzon') if metadata else None,
                'signguCd': metadata.get('signguCd') if metadata else None,
            },
            'data': {
                'items': normalized_items,
                'count': len(normalized_items)
            }
        }
        
        logger.info(f"Normalized {len(normalized_items)} 골목길 유동인구 items")
        
        return normalized

