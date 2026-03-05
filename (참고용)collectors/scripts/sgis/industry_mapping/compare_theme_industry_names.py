"""sgis_theme_codes_sub.md와 INDUSTRY_CODE_REFERENCE.md의 한글 명칭 비교"""

import re
from pathlib import Path

# sgis_theme_codes_sub.md 읽기
theme_file = Path("docs/sources/sgis/sgis_theme_codes_sub.md")
with open(theme_file, 'r', encoding='utf-8') as f:
    theme_content = f.read()

# theme_cd와 한글명 추출
theme_pattern = r'([^(]+)\((\d{3})\)'
theme_matches = re.findall(theme_pattern, theme_content)

print("=" * 80)
print("sgis_theme_codes_sub.md의 업종명과 업종구분코드 비교")
print("=" * 80)

# INDUSTRY_CODE_REFERENCE.md 읽기
industry_file = Path("docs/sources/sgis/INDUSTRY_CODE_REFERENCE.md")
with open(industry_file, 'r', encoding='utf-8') as f:
    industry_content = f.read()

# Level 2 (중분류) 추출
level2_pattern = r'\|\s*([A-Z]\d{2})\s*\|\s*([^|]+)\s*\|'
level2_matches = re.findall(level2_pattern, industry_content)

# Level 3 (소분류) 추출
level3_pattern = r'\|\s*([A-Z]\d{3})\s*\|\s*([^|]+)\s*\|'
level3_matches = re.findall(level3_pattern, industry_content)

# 딕셔너리로 변환 (업종명 -> 코드)
level2_dict = {name.strip(): code for code, name in level2_matches}
level3_dict = {name.strip(): code for code, name in level3_matches}

print(f"\n총 {len(theme_matches)}개의 theme_cd 항목 분석\n")

matched_level2 = []
matched_level3 = []
not_matched = []

for name, code in theme_matches:
    name = name.strip()
    
    # Level 2에서 찾기
    level2_code = None
    for industry_name, industry_code in level2_dict.items():
        # 정확히 일치하거나, theme_cd의 이름이 industry_name에 포함되거나
        if name == industry_name or name in industry_name or industry_name in name:
            # 더 정확한 매칭을 위해 추가 검증
            if name.replace(' ', '').replace('ㆍ', '·') == industry_name.replace(' ', '').replace('ㆍ', '·'):
                level2_code = industry_code
                break
            # 부분 일치도 확인
            elif len(name) > 5 and name[:10] in industry_name[:15]:
                level2_code = industry_code
                break
    
    # Level 3에서 찾기
    level3_code = None
    for industry_name, industry_code in level3_dict.items():
        if name == industry_name or name in industry_name or industry_name in name:
            if name.replace(' ', '').replace('ㆍ', '·') == industry_name.replace(' ', '').replace('ㆍ', '·'):
                level3_code = industry_code
                break
            elif len(name) > 5 and name[:10] in industry_name[:15]:
                level3_code = industry_code
                break
    
    if level2_code:
        matched_level2.append((code, name, level2_code))
    elif level3_code:
        matched_level3.append((code, name, level3_code))
    else:
        not_matched.append((code, name))

print(f"Level 2 (중분류)와 매칭: {len(matched_level2)}개")
print(f"Level 3 (소분류)와 매칭: {len(matched_level3)}개")
print(f"매칭되지 않음: {len(not_matched)}개\n")

print("\n" + "=" * 80)
print("Level 2 (중분류) 매칭 결과")
print("=" * 80)
for code, name, industry_code in matched_level2:
    print(f"theme_cd={code}: {name}")
    print(f"  → {industry_code}: {level2_dict.get(industry_code, 'N/A')}")

print("\n" + "=" * 80)
print("Level 3 (소분류) 매칭 결과")
print("=" * 80)
for code, name, industry_code in matched_level3:
    print(f"theme_cd={code}: {name}")
    print(f"  → {industry_code}: {level3_dict.get(industry_code, 'N/A')}")

print("\n" + "=" * 80)
print("매칭되지 않은 항목")
print("=" * 80)
for code, name in not_matched:
    print(f"theme_cd={code}: {name}")

# 수동으로 주요 항목들 확인
print("\n" + "=" * 80)
print("주요 항목 수동 확인")
print("=" * 80)

manual_checks = [
    ("의료용 물질 및 의약품 제조업", "C21"),
    ("전자부품, 컴퓨터, 영상, 음향 및 통신장비 제조업", "C26"),
    ("화학물질 및 화학제품 제조업", "C20"),
    ("식료품 제조업", "C10"),
    ("소프트웨어개발 및 공급업", "J62"),
    ("연구개발업", "M70"),
]

for name, expected_code in manual_checks:
    # Level 2에서 찾기
    found = False
    for industry_name, industry_code in level2_dict.items():
        if name in industry_name or industry_name in name:
            print(f"{name}")
            print(f"  → {industry_code}: {industry_name}")
            if industry_code == expected_code:
                print(f"  ✓ 예상 코드와 일치!")
            found = True
            break
    
    if not found:
        # Level 3에서 찾기
        for industry_name, industry_code in level3_dict.items():
            if name in industry_name or industry_name in name:
                print(f"{name}")
                print(f"  → {industry_code}: {industry_name}")
                found = True
                break
    
    if not found:
        print(f"{name} → 매칭되지 않음")

