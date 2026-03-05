"""11040 코드 API 디버깅."""

import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger

logger = get_logger(__name__)


def main():
    """11040 코드 API 응답 확인."""
    client = SBIZAPIClient()
    
    code = "11040"
    div_id = "signguCd"
    
    print(f"\n{'='*60}")
    print(f"테스트: 종로구 (코드: {code}, divId: {div_id})")
    print(f"{'='*60}")
    
    try:
        response = client.get_stores_by_dong(
            adong_cd=code,
            page_no=1,
            num_of_rows=5,
            div_id=div_id
        )
        
        print(f"\n응답 타입: {type(response)}")
        print(f"\n응답 내용:")
        print(json.dumps(response, ensure_ascii=False, indent=2)[:2000])
        
        # 응답 구조 분석
        if isinstance(response, dict):
            print(f"\n응답 키: {list(response.keys())}")
            
            if 'header' in response:
                header = response.get('header', {})
                print(f"resultCode: {header.get('resultCode', 'N/A')}")
                print(f"resultMsg: {header.get('resultMsg', 'N/A')}")
            
            if 'body' in response:
                body = response.get('body', {})
                print(f"body 키: {list(body.keys()) if isinstance(body, dict) else 'N/A'}")
                print(f"totalCount: {body.get('totalCount', 'N/A')}")
                
                items = body.get('items', [])
                print(f"items 타입: {type(items)}")
                if isinstance(items, list):
                    print(f"items 개수: {len(items)}")
                elif isinstance(items, dict):
                    print(f"items 키: {list(items.keys())}")
    
    except Exception as e:
        print(f"에러 발생: {e}")
        import traceback
        traceback.print_exc()
    
    client.close()


if __name__ == "__main__":
    main()

