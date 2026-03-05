"""
Backend Adapter for Framework Integration
Framework 프로젝트의 backend API와 통신하는 어댑터

이 모듈은 collectors 폴더에서 수집한 데이터를 backend API로 전송하는 역할을 합니다.
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BackendAdapter:
    """
    Backend API와 통신하는 어댑터 클래스
    
    수집 완료 후 backend의 Raw Store에 데이터를 전송합니다.
    """
    
    def __init__(self, backend_url: Optional[str] = None):
        """
        BackendAdapter 초기화
        
        Args:
            backend_url: Backend API 기본 URL (기본값: 환경 변수에서 읽기)
        """
        self.backend_url = backend_url or os.getenv(
            'BACKEND_API_URL', 
            'http://localhost:3000'
        )
        self.api_endpoint = f"{self.backend_url}/api/collectors/raw"
        
    def send_raw_data(
        self,
        collector_type: str,
        raw_data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        수집된 원시 데이터를 backend API로 전송
        
        Args:
            collector_type: 수집기 타입 (예: 'sgis', 'sbiz', 'openup')
            raw_data: 수집된 원시 데이터 (dict, list 등)
            metadata: 추가 메타데이터 (선택)
            
        Returns:
            API 응답 결과
            
        Raises:
            requests.RequestException: API 호출 실패 시
        """
        try:
            payload = {
                'collector_type': collector_type,
                'data': raw_data,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            logger.info(f"Sending data to backend: {collector_type}", {
                'endpoint': self.api_endpoint,
                'data_size': len(json.dumps(raw_data)) if isinstance(raw_data, (dict, list)) else 0
            })
            
            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Successfully sent data to backend: {collector_type}", {
                'status': result.get('status'),
                'message': result.get('message')
            })
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send data to backend: {collector_type}", {
                'error': str(e),
                'endpoint': self.api_endpoint
            })
            raise
    
    def check_backend_status(self) -> Dict[str, Any]:
        """
        Backend API 상태 확인
        
        Returns:
            Backend 상태 정보
        """
        try:
            health_endpoint = f"{self.backend_url}/api/health"
            response = requests.get(health_endpoint, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Backend health check failed: {e}")
            return {'status': 'unavailable', 'error': str(e)}
    
    def send_collection_result(
        self,
        collector_type: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        수집 결과를 backend로 전송
        
        Args:
            collector_type: 수집기 타입
            result: 수집 결과 (records_collected, errors 등 포함)
            
        Returns:
            API 응답 결과
        """
        metadata = {
            'records_collected': result.get('records_collected', 0),
            'errors': result.get('errors', []),
            'start_time': result.get('start_time'),
            'end_time': result.get('end_time')
        }
        
        return self.send_raw_data(
            collector_type=collector_type,
            raw_data=result.get('data', {}),
            metadata=metadata
        )


# 전역 인스턴스 (선택적 사용)
_backend_adapter: Optional[BackendAdapter] = None


def get_backend_adapter() -> BackendAdapter:
    """
    BackendAdapter 싱글톤 인스턴스 반환
    
    Returns:
        BackendAdapter 인스턴스
    """
    global _backend_adapter
    if _backend_adapter is None:
        _backend_adapter = BackendAdapter()
    return _backend_adapter

