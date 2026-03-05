"""theme_cd와 업종 분석 스크립트"""

import json
from collections import Counter, defaultdict
from pathlib import Path

# 성동구 데이터 로드
data_dir = Path("data/raw/sgis/20251130_214212")
json_file = data_dir / "sgis_technical_biz_20251130_214212.json"

if not json_file.exists():
    print(f"파일을 찾을 수 없습니다: {json_file}")
    exit(1)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('result', [])
print(f"총 {len(items)}개 항목 분석\n")

# theme_cd별 분류
theme_groups = defaultdict(list)
for item in items:
    theme_cd = item.get('theme_cd', '')
    theme_groups[theme_cd].append(item)

print("="*60)
print("theme_cd별 분석")
print("="*60)

for theme_cd in sorted(theme_groups.keys()):
    items_in_theme = theme_groups[theme_cd]
    print(f"\ntheme_cd={theme_cd}: {len(items_in_theme)}개 항목")
    
    # 회사명 샘플
    print("  회사명 샘플:")
    for item in items_in_theme[:10]:
        corp_nm = item.get('corp_nm', 'N/A')
        naddr = item.get('naddr', 'N/A')
        print(f"    - {corp_nm} ({naddr})")
    
    # 회사명 키워드 분석
    corp_keywords = []
    for item in items_in_theme:
        corp_nm = item.get('corp_nm', '')
        # 회사명에서 업종 관련 키워드 추출
        keywords = []
        if '바이오' in corp_nm or 'bio' in corp_nm.lower():
            keywords.append('바이오')
        if '전자' in corp_nm or 'elec' in corp_nm.lower():
            keywords.append('전자')
        if '정보' in corp_nm or 'info' in corp_nm.lower():
            keywords.append('정보')
        if '시스템' in corp_nm or 'system' in corp_nm.lower():
            keywords.append('시스템')
        if '기술' in corp_nm or 'tech' in corp_nm.lower():
            keywords.append('기술')
        if '금속' in corp_nm:
            keywords.append('금속')
        if '화학' in corp_nm or 'chem' in corp_nm.lower():
            keywords.append('화학')
        if '메디' in corp_nm or 'med' in corp_nm.lower():
            keywords.append('의료')
        corp_keywords.extend(keywords)
    
    keyword_counter = Counter(corp_keywords)
    if keyword_counter:
        print(f"  주요 키워드:")
        for keyword, count in keyword_counter.most_common(10):
            print(f"    {keyword}: {count}회")

print("\n" + "="*60)
print("결론")
print("="*60)
print("theme_cd는 기술업종을 분류하는 코드로 보입니다.")
print("업종구분코드(표준산업분류)와의 직접적인 매핑은")
print("SGIS 공식 문서나 추가 분석이 필요합니다.")

