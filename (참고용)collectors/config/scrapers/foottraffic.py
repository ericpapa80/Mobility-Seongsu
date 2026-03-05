"""Foottraffic scraper configuration."""

import os
from typing import Dict


class FoottrafficConfig:
    """Configuration for Foottraffic (골목길 유동인구) scraper."""
    
    @staticmethod
    def get_base_url() -> str:
        """Get 골목길 유동인구 base URL."""
        return os.getenv("FOOTTRAFFIC_BASE_URL", "https://golmok.seoul.go.kr")
    
    @staticmethod
    def get_endpoint() -> str:
        """Get API endpoint."""
        # 실제 API 엔드포인트: /tool/wfs/fpop.json
        return "/tool/wfs/fpop.json"
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get request headers."""
        base_url = FoottrafficConfig.get_base_url()
        return {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'ko,en;q=0.9,en-US;q=0.8',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': base_url,
            'pragma': 'no-cache',
            'referer': f'{base_url}/commercialArea/commercialArea.do',
            'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            'x-requested-with': 'XMLHttpRequest'
        }
    
    @staticmethod
    def get_seongsu_bounds() -> Dict[str, float]:
        """Get 성수동 좌표 범위 (2025년 3분기 기준)."""
        return {
            'minx': 187500.0169279298,
            'miny': 447034.7240779298,
            'maxx': 191408.0169279298,
            'maxy': 449596.2240779298
        }
    
    @staticmethod
    def validate() -> bool:
        """Validate Foottraffic configuration."""
        # No special validation needed for public API
        return True

