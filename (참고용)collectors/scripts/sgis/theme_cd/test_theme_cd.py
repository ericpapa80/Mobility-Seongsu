"""theme_cd 분석 스크립트"""

import json
from collections import Counter
from pathlib import Path

# 최근 수집된 성동구 데이터 확인
data_dir = Path("data/raw/sgis/20251130_214212")
json_file = data_dir / "sgis_technical_biz_20251130_214212.json"

if json_file.exists():
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('result', [])
    print(f"총 {len(items)}개 항목")
    
    # theme_cd 값들
    theme_cds = set([item.get('theme_cd', '') for item in items])
    print(f"\n수집된 theme_cd 값들: {sorted(theme_cds)}")
    
    # theme_cd 분포
    counter = Counter([item.get('theme_cd', '') for item in items])
    print(f"\ntheme_cd 분포:")
    for k, v in sorted(counter.items()):
        print(f"  {k}: {v}개 ({v/len(items)*100:.1f}%)")
    
    # 각 theme_cd별 샘플 회사명
    print(f"\ntheme_cd별 샘플 회사명:")
    for theme_cd in sorted(theme_cds):
        sample_items = [item for item in items if item.get('theme_cd') == theme_cd][:3]
        print(f"\n  theme_cd={theme_cd}:")
        for item in sample_items:
            print(f"    - {item.get('corp_nm', 'N/A')} ({item.get('naddr', 'N/A')})")
else:
    print(f"파일을 찾을 수 없습니다: {json_file}")

