"""
표준산업분류 연계표의 매핑 관계를 상세 분석하는 스크립트
"""

import json
from pathlib import Path
from collections import Counter, defaultdict

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent

def analyze_mapping_relationship():
    """표준산업분류 연계표의 매핑 관계 분석"""
    file_path = project_root / "docs" / "sources" / "sbiz" / "converted" / "소상공인시장진흥공단_상가(상권)정보_업종분류(2302)_및_연계표_v1_3. 표준산업분류(10차)_연계표.json"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 헤더 제외
    actual_data = [item for item in data if item.get("상가(상권)정보 업종분류(247개)") != "코드"]
    
    print("=" * 80)
    print("표준산업분류 연계표 매핑 관계 분석")
    print("=" * 80)
    print(f"총 매핑 레코드 수: {len(actual_data)}")
    
    # 상권 업종별로 몇 개의 표준산업분류에 매핑되는지 확인
    sbiz_to_standard = defaultdict(list)
    standard_to_sbiz = defaultdict(list)
    
    for item in actual_data:
        sbiz_code = item.get("상가(상권)정보 업종분류(247개)", "")
        standard_code = item.get("통계청 제10차 표준산업분류(277개)", "")
        
        if sbiz_code and standard_code:
            sbiz_to_standard[sbiz_code].append(standard_code)
            standard_to_sbiz[standard_code].append(sbiz_code)
    
    print(f"\n상권 업종분류 코드 수: {len(sbiz_to_standard)}")
    print(f"표준산업분류 코드 수: {len(standard_to_sbiz)}")
    
    # 상권 업종별 매핑 개수 분포
    mapping_counts = Counter(len(codes) for codes in sbiz_to_standard.values())
    
    print(f"\n상권 업종 → 표준산업분류 매핑 분포:")
    print(f"  (한 상권 업종이 몇 개의 표준산업분류에 매핑되는지)")
    for count in sorted(mapping_counts.keys()):
        num_codes = mapping_counts[count]
        print(f"  {count}개 매핑: {num_codes}개 상권 업종")
    
    # 표준산업분류별 매핑 개수 분포
    reverse_mapping_counts = Counter(len(codes) for codes in standard_to_sbiz.values())
    
    print(f"\n표준산업분류 → 상권 업종 매핑 분포:")
    print(f"  (한 표준산업분류가 몇 개의 상권 업종에 매핑되는지)")
    for count in sorted(reverse_mapping_counts.keys()):
        num_codes = reverse_mapping_counts[count]
        print(f"  {count}개 매핑: {num_codes}개 표준산업분류")
    
    # 샘플: 1:N 매핑 예시
    print(f"\n1:N 매핑 예시 (한 상권 업종이 여러 표준산업분류에 매핑):")
    count = 0
    for sbiz_code, standard_codes in sbiz_to_standard.items():
        if len(standard_codes) > 1:
            count += 1
            if count <= 5:
                # 상권 업종 정보 찾기
                sbiz_item = next((item for item in actual_data if item.get("상가(상권)정보 업종분류(247개)") == sbiz_code), None)
                if sbiz_item:
                    sbiz_name = f"{sbiz_item.get('Unnamed: 1', '')} > {sbiz_item.get('Unnamed: 2', '')} > {sbiz_item.get('Unnamed: 3', '')}"
                    print(f"\n  상권 업종: {sbiz_code} ({sbiz_name})")
                    print(f"  → {len(standard_codes)}개의 표준산업분류에 매핑:")
                    for std_code in standard_codes[:3]:  # 최대 3개만 표시
                        std_item = next((item for item in actual_data if item.get("통계청 제10차 표준산업분류(277개)") == std_code), None)
                        if std_item:
                            std_name = f"{std_item.get('Unnamed: 5', '')} > {std_item.get('Unnamed: 6', '')} > {std_item.get('Unnamed: 7', '')}"
                            print(f"    - {std_code} ({std_name})")
                    if len(standard_codes) > 3:
                        print(f"    ... 외 {len(standard_codes) - 3}개")
    
    # 샘플: N:1 매핑 예시
    print(f"\nN:1 매핑 예시 (여러 상권 업종이 한 표준산업분류에 매핑):")
    count = 0
    for standard_code, sbiz_codes in standard_to_sbiz.items():
        if len(sbiz_codes) > 1:
            count += 1
            if count <= 5:
                # 표준산업분류 정보 찾기
                std_item = next((item for item in actual_data if item.get("통계청 제10차 표준산업분류(277개)") == standard_code), None)
                if std_item:
                    std_name = f"{std_item.get('Unnamed: 5', '')} > {std_item.get('Unnamed: 6', '')} > {std_item.get('Unnamed: 7', '')}"
                    print(f"\n  표준산업분류: {standard_code} ({std_name})")
                    print(f"  ← {len(sbiz_codes)}개의 상권 업종이 매핑:")
                    for sbiz_code in sbiz_codes[:3]:  # 최대 3개만 표시
                        sbiz_item = next((item for item in actual_data if item.get("상가(상권)정보 업종분류(247개)") == sbiz_code), None)
                        if sbiz_item:
                            sbiz_name = f"{sbiz_item.get('Unnamed: 1', '')} > {sbiz_item.get('Unnamed: 2', '')} > {sbiz_item.get('Unnamed: 3', '')}"
                            print(f"    - {sbiz_code} ({sbiz_name})")
                    if len(sbiz_codes) > 3:
                        print(f"    ... 외 {len(sbiz_codes) - 3}개")
    
    # 통합 여부 분석
    print("\n" + "=" * 80)
    print("통합 여부 분석")
    print("=" * 80)
    
    # 1:1 매핑 비율
    one_to_one = sum(1 for codes in sbiz_to_standard.values() if len(codes) == 1)
    one_to_many = sum(1 for codes in sbiz_to_standard.values() if len(codes) > 1)
    
    print(f"\n상권 업종 → 표준산업분류:")
    print(f"  1:1 매핑: {one_to_one}개 ({one_to_one/len(sbiz_to_standard)*100:.1f}%)")
    print(f"  1:N 매핑: {one_to_many}개 ({one_to_many/len(sbiz_to_standard)*100:.1f}%)")
    
    # N:1 매핑 비율
    many_to_one_std = sum(1 for codes in standard_to_sbiz.values() if len(codes) > 1)
    one_to_one_std = sum(1 for codes in standard_to_sbiz.values() if len(codes) == 1)
    
    print(f"\n표준산업분류 → 상권 업종:")
    print(f"  1:1 매핑: {one_to_one_std}개 ({one_to_one_std/len(standard_to_sbiz)*100:.1f}%)")
    print(f"  N:1 매핑: {many_to_one_std}개 ({many_to_one_std/len(standard_to_sbiz)*100:.1f}%)")
    
    print(f"\n결론:")
    if one_to_many > 0 or many_to_one_std > 0:
        print(f"  - 완전한 통합이 아닙니다.")
        print(f"  - 일부 상권 업종은 여러 표준산업분류에 매핑됩니다 (1:N)")
        print(f"  - 일부 표준산업분류는 여러 상권 업종을 포함합니다 (N:1)")
        print(f"  - 이는 상권 업종과 표준산업분류의 분류 기준이 다르기 때문입니다.")
    else:
        print(f"  - 모든 매핑이 1:1입니다.")
        print(f"  - 완전한 통합 관계입니다.")


if __name__ == "__main__":
    analyze_mapping_relationship()
