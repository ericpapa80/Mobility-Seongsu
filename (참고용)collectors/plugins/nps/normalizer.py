"""NPS data normalizer for converting raw NPS data to common schema."""

import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.normalizers import BaseNormalizer
from core.logger import get_logger

logger = get_logger(__name__)


class NPSNormalizer(BaseNormalizer):
    """Normalizer for NPS workplace data.
    
    Converts NPS CSV data to common schema format.
    """
    
    def __init__(self):
        """Initialize NPS normalizer."""
        super().__init__(source_name="nps")
    
    def normalize(self, raw_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize NPS data to common schema.
        
        Args:
            raw_data: Raw NPS data dictionary with 'records' list
            metadata: Optional metadata (csv_source, filter_address, etc.)
            
        Returns:
            Normalized data in common schema format
        """
        records = raw_data.get('records', [])
        
        # Normalize each record
        normalized_items = []
        for record in records:
            normalized_item = {
                'id': str(record.get('사업자등록번호', '')),
                'name': record.get('사업장명', ''),
                'address': {
                    'full': record.get('주소', ''),
                    'postal_code': record.get('우편번호', ''),
                    'detail': record.get('사업장지번상세주소', ''),
                    'sido': record.get('시도', ''),
                    'administrative_codes': {
                        'legal_dong': record.get('고객법정동주소코드', ''),
                        'admin_dong': record.get('고객행정동주소코드', ''),
                        'sido_code': record.get('시도코드', ''),
                        'sigungu_code': record.get('시군구코드', ''),
                        'eupmyeondong_code': record.get('읍면동코드', '')
                    }
                },
                'coordinates': {
                    'x': record.get('x') or record.get('lon'),
                    'y': record.get('y') or record.get('lat')
                } if (record.get('x') is not None or record.get('lon') is not None) else None,
                'business': {
                    'registration_number': record.get('사업자등록번호', ''),
                    'type_code': record.get('사업장형태구분코드', ''),
                    'industry_code': record.get('업종코드', ''),
                    'industry_name': record.get('업종코드명', '')
                },
                'pension': {
                    'status': record.get('가입상태', ''),
                    'members_count': record.get('가입자수', 0),
                    'amount': record.get('금액', 0),
                    'new_members': record.get('신규', 0),
                    'lost_members': record.get('상실', 0),
                    'per_person_amount': record.get('인당금액', 0),
                    'estimated_monthly_salary': record.get('월급여추정', 0),
                    'estimated_annual_salary': record.get('연간급여추정', 0)
                },
                'dates': {
                    'application_date': record.get('적용일자', ''),
                    're_registration_date': record.get('재등록일자', ''),
                    'withdrawal_date': record.get('탈퇴일자', ''),
                    'withdrawal_year': record.get('탈퇴일자_연도', None),
                    'withdrawal_month': record.get('탈퇴일자_월', None),
                    'data_generation_month': record.get('자료생성년월', '')
                },
                'raw': record  # Keep original data for reference
            }
            normalized_items.append(normalized_item)
        
        # Build normalized structure
        normalized = {
            'metadata': self._get_common_metadata(metadata),
            'source_specific': {
                'csv_source': metadata.get('csv_source') if metadata else None,
                'filter_address': metadata.get('filter_address') if metadata else None,
                'filter_active_only': metadata.get('filter_active_only') if metadata else None,
                'total_count': metadata.get('total_count') if metadata else len(normalized_items),
            },
            'data': {
                'items': normalized_items,
                'count': len(normalized_items)
            }
        }
        
        logger.info(f"Normalized {len(normalized_items)} NPS workplace records")
        
        return normalized

