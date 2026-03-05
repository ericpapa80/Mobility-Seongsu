"""theme_cd와 업종 코드 비교 분석 스크립트"""

import json
from collections import Counter, defaultdict
from pathlib import Path
import re

# 데이터 파일 경로
data_file = Path("data/raw/sgis/20251130_213637/sgis_technical_biz_20251130_213637.json")
industry_ref_file = Path("docs/sources/sgis/INDUSTRY_CODE_REFERENCE.md")

# 데이터 로드
print("="*80)
print("1. 데이터 로드")
print("="*80)

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('result', [])
print(f"총 {len(items)}개 항목 로드됨")

# theme_cd별 그룹화
theme_groups = defaultdict(list)
for item in items:
    theme_cd = item.get('theme_cd', '')
    theme_groups[theme_cd].append(item)

print(f"\ntheme_cd 종류: {sorted(theme_groups.keys())}")
print(f"\ntheme_cd별 개수:")
for theme_cd in sorted(theme_groups.keys()):
    print(f"  {theme_cd}: {len(theme_groups[theme_cd])}개")

# 업종 코드 참조 문서 로드
print("\n" + "="*80)
print("2. 업종 코드 참조 문서 분석")
print("="*80)

industry_codes = {}
if industry_ref_file.exists():
    with open(industry_ref_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 표 형식에서 코드와 업종명 추출
    # | 코드 | 업종명 | 형식 찾기
    pattern = r'\|\s*([A-Z]\d+)\s*\|\s*([^|]+)\s*\|'
    matches = re.findall(pattern, content)
    
    for code, name in matches:
        industry_codes[code] = name.strip()
    
    print(f"업종 코드 {len(industry_codes)}개 로드됨")
    print(f"대분류 코드 예시: {sorted(set([c[0] for c in industry_codes.keys()]))}")
else:
    print("업종 코드 참조 문서를 찾을 수 없습니다.")

# theme_cd별 회사명 키워드 분석
print("\n" + "="*80)
print("3. theme_cd별 회사명 키워드 분석")
print("="*80)

# 업종 관련 키워드 매핑 (업종 코드와 연관)
industry_keywords = {
    '바이오': ['C211', 'C212', 'C213', 'C271'],  # 의약품, 의료용품
    '전자': ['C261', 'C262', 'C263', 'C264'],  # 반도체, 전자부품
    '정보': ['J58', 'J59', 'J60', 'J61', 'J62', 'J63'],  # 정보통신업
    '시스템': ['J62', 'J63'],  # 컴퓨터 프로그래밍, 정보서비스
    '기술': ['M70', 'M71', 'M72', 'M73', 'M74', 'M75'],  # 전문과학기술서비스
    '금속': ['C241', 'C242', 'C243', 'C251', 'C252', 'C259'],  # 금속제조
    '화학': ['C20', 'C201', 'C202', 'C203', 'C204', 'C205'],  # 화학제품
    '의료': ['C211', 'C212', 'C213', 'C271', 'Q86'],  # 의약품, 보건업
    '소프트웨어': ['J62', 'J63'],  # 소프트웨어 개발
    '반도체': ['C261'],  # 반도체
    '통신': ['J61', 'C264'],  # 통신
    '기계': ['C291', 'C292'],  # 기계제조
    '자동차': ['C301', 'C302', 'C303', 'C304'],  # 자동차
    '에너지': ['D351', 'C191', 'C192'],  # 전기, 석유
    '건설': ['F411', 'F412', 'F421', 'F422', 'F423', 'F424', 'F425'],  # 건설
}

for theme_cd in sorted(theme_groups.keys()):
    items_in_theme = theme_groups[theme_cd]
    print(f"\n{'='*60}")
    print(f"theme_cd={theme_cd}: {len(items_in_theme)}개 항목")
    print(f"{'='*60}")
    
    # 회사명 샘플 (상위 20개)
    print("\n회사명 샘플:")
    for i, item in enumerate(items_in_theme[:20], 1):
        corp_nm = item.get('corp_nm', 'N/A')
        naddr = item.get('naddr', 'N/A')
        print(f"  {i:2d}. {corp_nm} ({naddr})")
    
    # 키워드 분석
    keyword_matches = defaultdict(int)
    for item in items_in_theme:
        corp_nm = item.get('corp_nm', '').lower()
        for keyword, codes in industry_keywords.items():
            if keyword in corp_nm:
                for code in codes:
                    keyword_matches[code] += 1
    
    if keyword_matches:
        print("\n추정 업종 코드 (회사명 키워드 기반):")
        for code, count in sorted(keyword_matches.items(), key=lambda x: x[1], reverse=True)[:10]:
            industry_name = industry_codes.get(code, '알 수 없음')
            print(f"  {code} ({industry_name}): {count}회 매칭")

# 결론
print("\n" + "="*80)
print("4. 결론 및 분석")
print("="*80)

print("""
theme_cd는 SGIS 기술업종 통계지도에서 사용하는 테마 코드입니다.
업종구분코드(표준산업분류)와의 직접적인 매핑 관계는:

1. theme_cd는 기술업종을 대분류하는 코드로 보입니다 (예: 110, 111, 112 등)
2. 업종구분코드는 표준산업분류 체계를 따르는 상세한 코드입니다 (예: C261, J62 등)
3. theme_cd 하나가 여러 업종구분코드를 포함할 수 있습니다
4. 회사명 키워드 분석을 통해 어느 정도 추정은 가능하나, 정확한 매핑은 SGIS 공식 문서가 필요합니다

권장사항:
- SGIS 개발자 지원센터에서 theme_cd와 업종구분코드의 매핑 테이블 확인
- 또는 각 theme_cd별로 실제 회사들의 사업자등록번호를 통해 정확한 업종 확인
""")

