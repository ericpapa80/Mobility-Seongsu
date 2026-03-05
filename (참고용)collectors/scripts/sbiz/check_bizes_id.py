"""상가업소 번호 필드 확인."""

import json
from pathlib import Path

# JSON 파일 읽기
json_file = Path('data/raw/sbiz/sbiz_stores_seongsu_extracted_20251202_094917/sbiz_stores_seongsu_20251202_094917.json')

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 첫 번째 업소 예시
if data['stores']:
    store = data['stores'][0]
    
    print("=" * 60)
    print("상가업소 번호 필드 정보")
    print("=" * 60)
    
    print(f"\n필드명: bizesId")
    print(f"값: {store.get('bizesId', 'N/A')}")
    print(f"타입: {type(store.get('bizesId')).__name__}")
    
    print(f"\n첫 번째 업소 전체 정보:")
    print(f"  상가업소번호 (bizesId): {store.get('bizesId')}")
    print(f"  상호명 (bizesNm): {store.get('bizesNm')}")
    print(f"  지점명 (brchNm): {store.get('brchNm') or '(없음)'}")
    print(f"  행정동 (adongNm): {store.get('adongNm')}")
    print(f"  주소: {store.get('lnoAdr')}")
    
    print(f"\n상가업소 번호 형식 분석:")
    bizes_id = store.get('bizesId', '')
    if bizes_id:
        print(f"  전체: {bizes_id}")
        print(f"  길이: {len(bizes_id)}자")
        print(f"  형식: {bizes_id[:2]}-{bizes_id[2:8]}-{bizes_id[8:]}")
    
    # 여러 업소의 상가업소 번호 예시
    print(f"\n다양한 상가업소 번호 예시 (최대 10개):")
    for i, s in enumerate(data['stores'][:10], 1):
        print(f"  {i}. {s.get('bizesId')} - {s.get('bizesNm')} ({s.get('adongNm')})")
    
    # 상가업소 번호 패턴 분석
    print(f"\n상가업소 번호 패턴:")
    prefixes = {}
    for s in data['stores']:
        prefix = s.get('bizesId', '')[:2] if s.get('bizesId') else ''
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
    
    for prefix, count in sorted(prefixes.items()):
        print(f"  {prefix}로 시작: {count:,}개")

