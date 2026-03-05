"""성동구 행정구역 코드 찾기 스크립트"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.sgis.scraper import SGISScraper

# 성동구로 추정되는 코드들
possible_codes = [
    ('11200', '성동구 (표준 코드)'),
    ('11560', '성동구 (대안 1)'),
    ('11210', '성동구 (대안 2)'),
    ('11220', '성동구 (대안 3)'),
    ('11230', '성동구 (대안 4)'),
]

def test_code(code, description):
    """특정 코드로 데이터 수집 테스트"""
    print(f"\n{'='*60}")
    print(f"테스트: {code} - {description}")
    print('='*60)
    
    try:
        scraper = SGISScraper()
        result = scraper.scrape(
            year=2023,
            adm_cd=code,
            save_json=False,
            save_csv=False
        )
        
        data = result.get('data', {})
        
        if 'errMsg' in data:
            print(f"❌ 오류: {data.get('errMsg')}")
            return False
        
        items = data.get('result', [])
        if not items:
            print("❌ 데이터 없음")
            return False
        
        # 주소에서 구 이름 추출
        addresses = [item.get('naddr', '') for item in items[:20] if item.get('naddr')]
        gu_names = set()
        for addr in addresses:
            parts = addr.split()
            if len(parts) > 1:
                gu_names.add(parts[1])
        
        print(f"✅ 데이터 항목 수: {len(items)}")
        print(f"주소 샘플:")
        for addr in addresses[:3]:
            print(f"  - {addr}")
        print(f"수집된 구 이름: {gu_names}")
        
        if '성동구' in gu_names:
            print(f"\n🎉 성공! {code}가 성동구 코드입니다!")
            return True
        else:
            print(f"\n⚠️  주의: {code}는 {gu_names} 데이터를 반환했습니다.")
            return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False
    finally:
        scraper.close()

def main():
    print("성동구 행정구역 코드 찾기")
    print("="*60)
    
    found = False
    for code, description in possible_codes:
        if test_code(code, description):
            found = True
            print(f"\n✅ 성동구 코드: {code}")
            break
    
    if not found:
        print("\n⚠️  성동구 코드를 찾지 못했습니다.")
        print("다른 코드를 시도하거나 SGIS 공식 문서를 확인하세요.")

if __name__ == "__main__":
    main()

