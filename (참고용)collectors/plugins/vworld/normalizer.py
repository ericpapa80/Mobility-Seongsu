"""VWorld data normalizer for converting raw VWorld data to common schema."""

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.normalizers import BaseNormalizer
from core.logger import get_logger

logger = get_logger(__name__)


class VWorldNormalizer(BaseNormalizer):
    """Normalizer for VWorld WFS 2.0 data.
    
    Converts VWorld API response to common schema format.
    """
    
    def __init__(self):
        """Initialize VWorld normalizer."""
        super().__init__(source_name="vworld")
    
    def normalize(self, raw_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize VWorld data to common schema.
        
        Args:
            raw_data: Raw VWorld API response
            metadata: Optional metadata (layer_id, bbox, etc.)
            
        Returns:
            Normalized data in common schema format
        """
        normalized_items = []
        
        # Handle Data API response format
        if 'response' in raw_data:
            response = raw_data['response']
            
            if response.get('status') == 'OK':
                result = response.get('result', {})
                feature_collection = result.get('featureCollection', {})
                features = feature_collection.get('features', [])
                
                for feature in features:
                    normalized_item = self._normalize_feature(feature, metadata)
                    if normalized_item:
                        normalized_items.append(normalized_item)
        
        # Handle WFS GeoJSON format
        elif 'features' in raw_data:
            features = raw_data['features']
            
            for feature in features:
                normalized_item = self._normalize_feature(feature, metadata)
                if normalized_item:
                    normalized_items.append(normalized_item)
        
        # Handle direct feature list
        elif isinstance(raw_data, list):
            for feature in raw_data:
                normalized_item = self._normalize_feature(feature, metadata)
                if normalized_item:
                    normalized_items.append(normalized_item)
        
        # Build normalized structure
        normalized = {
            'metadata': self._get_common_metadata(metadata),
            'source_specific': {
                'layer_id': metadata.get('layer_id') if metadata else None,
                'api_type': metadata.get('api_type') if metadata else None,
                'crs': metadata.get('crs') if metadata else None,
            },
            'data': {
                'items': normalized_items,
                'count': len(normalized_items)
            }
        }
        
        # Add total count if available
        if 'response' in raw_data:
            response = raw_data['response']
            if 'record' in response:
                normalized['data']['total'] = response['record'].get('total', len(normalized_items))
        
        logger.info(f"Normalized {len(normalized_items)} VWorld features")
        
        return normalized
    
    def _normalize_feature(self, feature: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize a single feature.
        
        Args:
            feature: Feature dictionary from VWorld API
            metadata: Optional metadata
            
        Returns:
            Normalized feature dictionary or None if invalid
        """
        if not isinstance(feature, dict):
            return None
        
        # Extract properties
        properties = feature.get('properties', {})
        
        # Extract geometry
        geometry = feature.get('geometry', {})
        
        # Build normalized feature
        normalized_item = {
            'id': properties.get('gid') or properties.get('id') or feature.get('id'),
            'properties': properties,
            'geometry': geometry,
            'raw': feature  # Keep original data for reference
        }
        
        # Add common fields if available
        if 'pnu' in properties:
            normalized_item['pnu'] = properties['pnu']
        if 'sido_nm' in properties:
            normalized_item['sido'] = properties['sido_nm']
        if 'sgg_nm' in properties:
            normalized_item['sigungu'] = properties['sgg_nm']
        if 'emd_nm' in properties:
            normalized_item['emd'] = properties['emd_nm']
        if 'jibun' in properties:
            normalized_item['jibun'] = properties['jibun']
        if 'rn_nm' in properties:
            normalized_item['road_name'] = properties['rn_nm']
        
        # Extract coordinates from geometry if available
        if geometry and 'coordinates' in geometry:
            coords = geometry['coordinates']
            if geometry.get('type') == 'Point' and len(coords) >= 2:
                normalized_item['coordinates'] = {
                    'x': coords[0],
                    'y': coords[1],
                    'lon': coords[0] if metadata and metadata.get('crs') == 'EPSG:4326' else None,
                    'lat': coords[1] if metadata and metadata.get('crs') == 'EPSG:4326' else None
                }
        
        return normalized_item
