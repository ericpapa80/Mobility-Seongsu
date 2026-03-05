"""
소상공인시장진흥공단 업종분류 파일들의 내용과 연관 관계를 분석하는 스크립트
"""

import json
import sys
from pathlib import Path
from collections import Counter

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def analyze_file_1():
    """파일 1: 상권_업종분류(247).json 분석"""
    file_path = project_root / "docs" / "sources" / "sbiz" / "converted" / "소상공인시장진흥공단_상가(상권)정보_업종분류(2302)_및_연계표_v1_1. 상권_업종분류(247).json"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("파일 1: 상권_업종분류(247).json")
    print("=" * 80)
    print(f"총 레코드 수: {len(data)}")
    
    # 헤더 제외
    actual_data = [item for item in data if item.get("상가(상권)정보 업종분류(247개)") != "대분류코드"]
    print(f"실제 데이터 레코드 수: {len(actual_data)}")
    
    # 대분류 코드 수집
    large_categories = set()
    medium_categories = set()
    small_categories = set()
    
    for item in actual_data:
        large_code = item.get("상가(상권)정보 업종분류(247개)", "")
        medium_code = item.get("Unnamed: 2", "")
        small_code = item.get("Unnamed: 4", "")
        
        if large_code:
            large_categories.add(large_code)
        if medium_code:
            medium_categories.add(medium_code)
        if small_code:
            small_categories.add(small_code)
    
    print(f"\n분류 계층 구조:")
    print(f"  대분류 코드 수: {len(large_categories)}")
    print(f"  중분류 코드 수: {len(medium_categories)}")
    print(f"  소분류 코드 수: {len(small_categories)}")
    
    # 샘플 데이터
    print(f"\n샘플 데이터 (처음 3개):")
    for i, item in enumerate(actual_data[:3]):
        print(f"  {i+1}. {item.get('Unnamed: 1', '')} > {item.get('Unnamed: 3', '')} > {item.get('Unnamed: 5', '')}")
        print(f"     코드: {item.get('상가(상권)정보 업종분류(247개)', '')} > {item.get('Unnamed: 2', '')} > {item.get('Unnamed: 4', '')}")
    
    return actual_data, small_categories


def analyze_file_2():
    """파일 2: 상권_업종연계표(837-247).json 분석"""
    file_path = project_root / "docs" / "sources" / "sbiz" / "converted" / "소상공인시장진흥공단_상가(상권)정보_업종분류(2302)_및_연계표_v1_2. 상권_업종연계표(837-247).json"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "=" * 80)
    print("파일 2: 상권_업종연계표(837-247).json")
    print("=" * 80)
    print(f"총 레코드 수: {len(data)}")
    
    # 헤더 제외
    actual_data = [item for item in data if item.get("상가(상권)정보 기존 업종분류(837개)") != "코드"]
    print(f"실제 데이터 레코드 수: {len(actual_data)}")
    
    # 기존 코드와 신규 코드 수집
    old_codes = set()
    new_codes = set()
    note_types = Counter()
    
    for item in actual_data:
        old_code = item.get("상가(상권)정보 기존 업종분류(837개)", "")
        new_code = item.get("상가(상권)정보 신규 업종분류(247개)", "")
        note = item.get("Unnamed: 8", "")
        
        if old_code:
            old_codes.add(old_code)
        if new_code:
            new_codes.add(new_code)
        if note:
            note_types[note] += 1
    
    print(f"\n코드 매핑 정보:")
    print(f"  기존 업종분류(837개) 코드 수: {len(old_codes)}")
    print(f"  신규 업종분류(247개) 코드 수: {len(new_codes)}")
    print(f"  매핑 관계 수: {len(actual_data)}")
    
    print(f"\n비고 유형:")
    for note_type, count in note_types.most_common():
        print(f"  {note_type}: {count}건")
    
    # 샘플 데이터
    print(f"\n샘플 데이터 (처음 3개):")
    for i, item in enumerate(actual_data[:3]):
        old_name = f"{item.get('Unnamed: 1', '')} > {item.get('Unnamed: 2', '')} > {item.get('Unnamed: 3', '')}"
        new_name = f"{item.get('Unnamed: 5', '')} > {item.get('Unnamed: 6', '')} > {item.get('Unnamed: 7', '')}"
        print(f"  {i+1}. 기존: {item.get('상가(상권)정보 기존 업종분류(837개)', '')} ({old_name})")
        print(f"     신규: {item.get('상가(상권)정보 신규 업종분류(247개)', '')} ({new_name})")
        print(f"     비고: {item.get('Unnamed: 8', '')}")
    
    return actual_data, new_codes


def analyze_file_3():
    """파일 3: 표준산업분류(10차)_연계표.json 분석"""
    file_path = project_root / "docs" / "sources" / "sbiz" / "converted" / "소상공인시장진흥공단_상가(상권)정보_업종분류(2302)_및_연계표_v1_3. 표준산업분류(10차)_연계표.json"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "=" * 80)
    print("파일 3: 표준산업분류(10차)_연계표.json")
    print("=" * 80)
    print(f"총 레코드 수: {len(data)}")
    
    # 헤더 제외
    actual_data = [item for item in data if item.get("상가(상권)정보 업종분류(247개)") != "코드"]
    print(f"실제 데이터 레코드 수: {len(actual_data)}")
    
    # 상권 업종 코드와 표준산업분류 코드 수집
    sbiz_codes = set()
    standard_codes = set()
    
    for item in actual_data:
        sbiz_code = item.get("상가(상권)정보 업종분류(247개)", "")
        standard_code = item.get("통계청 제10차 표준산업분류(277개)", "")
        
        if sbiz_code:
            sbiz_codes.add(sbiz_code)
        if standard_code:
            standard_codes.add(standard_code)
    
    print(f"\n코드 매핑 정보:")
    print(f"  상권 업종분류(247개) 코드 수: {len(sbiz_codes)}")
    print(f"  표준산업분류(10차, 277개) 코드 수: {len(standard_codes)}")
    print(f"  매핑 관계 수: {len(actual_data)}")
    
    # 샘플 데이터
    print(f"\n샘플 데이터 (처음 3개):")
    for i, item in enumerate(actual_data[:3]):
        sbiz_name = f"{item.get('Unnamed: 1', '')} > {item.get('Unnamed: 2', '')} > {item.get('Unnamed: 3', '')}"
        standard_name = f"{item.get('Unnamed: 5', '')} > {item.get('Unnamed: 6', '')} > {item.get('Unnamed: 7', '')} > {item.get('Unnamed: 8', '')} > {item.get('Unnamed: 9', '')}"
        print(f"  {i+1}. 상권 업종: {item.get('상가(상권)정보 업종분류(247개)', '')} ({sbiz_name})")
        print(f"     표준산업분류: {item.get('통계청 제10차 표준산업분류(277개)', '')} ({standard_name})")
    
    return actual_data, sbiz_codes


def analyze_relationships(data1, codes1, data2, codes2, data3, codes3):
    """3개 파일 간의 연관 관계 분석"""
    print("\n" + "=" * 80)
    print("파일 간 연관 관계 분석")
    print("=" * 80)
    
    # 파일 1과 파일 2의 관계
    print("\n1. 파일 1 ↔ 파일 2 관계:")
    print("   - 파일 1: 상권 업종분류 247개 (신규 분류 체계)")
    print("   - 파일 2: 기존 837개 → 신규 247개 매핑표")
    print("   - 관계: 파일 2의 '신규 업종분류(247개)' 코드가 파일 1의 소분류 코드와 일치")
    
    overlap_1_2 = codes1.intersection(codes2)
    print(f"   - 공통 코드 수: {len(overlap_1_2)}")
    print(f"   - 파일 1에만 있는 코드: {len(codes1 - codes2)}")
    print(f"   - 파일 2에만 있는 코드: {len(codes2 - codes1)}")
    
    # 파일 1과 파일 3의 관계
    print("\n2. 파일 1 ↔ 파일 3 관계:")
    print("   - 파일 1: 상권 업종분류 247개 (신규 분류 체계)")
    print("   - 파일 3: 상권 업종분류 247개 ↔ 표준산업분류 10차 매핑표")
    print("   - 관계: 파일 3의 '상권 업종분류(247개)' 코드가 파일 1의 소분류 코드와 일치")
    
    overlap_1_3 = codes1.intersection(codes3)
    print(f"   - 공통 코드 수: {len(overlap_1_3)}")
    print(f"   - 파일 1에만 있는 코드: {len(codes1 - codes3)}")
    print(f"   - 파일 3에만 있는 코드: {len(codes3 - codes1)}")
    
    # 파일 2와 파일 3의 관계
    print("\n3. 파일 2 ↔ 파일 3 관계:")
    print("   - 파일 2: 기존 837개 → 신규 247개 매핑표")
    print("   - 파일 3: 상권 업종분류 247개 ↔ 표준산업분류 10차 매핑표")
    print("   - 관계: 두 파일 모두 신규 247개 분류를 사용하므로 연결 가능")
    
    overlap_2_3 = codes2.intersection(codes3)
    print(f"   - 공통 코드 수 (신규 247개): {len(overlap_2_3)}")
    
    # 전체 관계도
    print("\n" + "=" * 80)
    print("전체 관계도")
    print("=" * 80)
    print("""
    [기존 업종분류 837개]
           ↓ (파일 2: 매핑)
    [신규 업종분류 247개] ←→ (파일 1: 분류 체계 정의)
           ↓ (파일 3: 매핑)
    [표준산업분류 10차 277개]
    
    설명:
    1. 파일 1: 신규 업종분류 247개의 계층 구조 정의 (대분류 > 중분류 > 소분류)
    2. 파일 2: 기존 837개 분류를 신규 247개로 통합/변경하는 매핑표
    3. 파일 3: 신규 247개 분류를 통계청 표준산업분류 10차와 연계하는 매핑표
    
    활용:
    - 기존 데이터(837개) → 파일 2 → 신규 데이터(247개)
    - 신규 데이터(247개) → 파일 1 → 분류 정보 조회
    - 신규 데이터(247개) → 파일 3 → 표준산업분류 코드 조회
    """)


def main():
    """메인 함수"""
    print("소상공인시장진흥공단 업종분류 파일 분석")
    print("=" * 80)
    
    # 각 파일 분석
    data1, codes1 = analyze_file_1()
    data2, codes2 = analyze_file_2()
    data3, codes3 = analyze_file_3()
    
    # 연관 관계 분석
    analyze_relationships(data1, codes1, data2, codes2, data3, codes3)


if __name__ == "__main__":
    main()
