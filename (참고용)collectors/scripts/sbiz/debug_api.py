"""SBIZ API 디버깅 스크립트."""

import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger

logger = get_logger(__name__)


def main():
    """API 응답 구조 확인."""
    client = SBIZAPIClient()
    
    # 성수동 행정동 코드들
    test_codes = [
        ("11545510", "성수1동"),
        ("11545520", "성수2가동"),
        ("11545", "성동구"),  # 시군구 코드로도 시도
    ]
    
    for code, name in test_codes:
        print(f"\n{'='*60}")
        print(f"테스트: {name} (코드: {code})")
        print(f"{'='*60}")
        
        try:
            response = client.get_stores_by_dong(
                adong_cd=code,
                page_no=1,
                num_of_rows=5  # 작은 수로 테스트
            )
            
            print(f"\n응답 타입: {type(response)}")
            print(f"\n응답 내용 (처음 1000자):")
            print(json.dumps(response, ensure_ascii=False, indent=2)[:1000])
            
            # 응답 구조 분석
            if isinstance(response, dict):
                print(f"\n응답 키: {list(response.keys())}")
                
                if 'response' in response:
                    body = response.get('response', {}).get('body', {})
                    print(f"body 키: {list(body.keys()) if isinstance(body, dict) else 'N/A'}")
                    print(f"totalCount: {body.get('totalCount', 'N/A')}")
                    
                    items = body.get('items', {})
                    print(f"items 타입: {type(items)}")
                    if isinstance(items, dict):
                        print(f"items 키: {list(items.keys())}")
                        item = items.get('item')
                        if item:
                            print(f"item 타입: {type(item)}")
                            if isinstance(item, list):
                                print(f"item 개수: {len(item)}")
                            elif isinstance(item, dict):
                                print(f"item 키: {list(item.keys())[:10]}")
        
        except Exception as e:
            print(f"에러 발생: {e}")
            import traceback
            traceback.print_exc()
    
    client.close()


if __name__ == "__main__":
    main()

