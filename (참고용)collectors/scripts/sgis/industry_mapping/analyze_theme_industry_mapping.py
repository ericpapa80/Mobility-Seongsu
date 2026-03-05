"""theme_cd와 업종구분코드의 한글명 비교 분석"""

# theme_cd의 업종명과 업종구분코드 비교
theme_items = [
    ("110", "의료용 물질 및 의약품 제조업"),
    ("111", "전자부품, 컴퓨터, 영상, 음향 및 통신장비 제조업"),
    ("112", "의료, 정밀, 광학기기 및 시계제조업"),
    ("113", "항공기, 우주선 및 부품 제조업"),
    ("120", "화학물질 및 화학제품 제조업"),
    ("121", "전기장비 제조업"),
    ("122", "기타 기계 및 장비 제조업"),
    ("123", "자동차 및 트레일러 제조업"),
    ("124", "기타 운송장비 제조업"),
    ("130", "코크스, 연탄 및 석유정제품 제조업"),
    ("131", "고무제품 및 플라스틱 제조업"),
    ("132", "비금속 광물제품 제조업"),
    ("133", "1차 금속 제조업"),
    ("134", "금속가공제품 제조업"),
    ("135", "선박 및 보트 건조업"),
    ("140", "식료품 제조업"),
    ("141", "음료 제조업"),
    ("142", "담배 제조업"),
    ("143", "섬유제품 제조업_의복복 제외"),
    ("144", "의복, 의복액세서리 및 모피제품 제조업"),
    ("145", "가죽 가방 및 신발 제조업"),
    ("146", "목재 및 나무제품 제조업"),
    ("147", "펄프, 종이 및 종이제품 제조업"),
    ("148", "인쇄 및 기록매체 복제업"),
    ("149", "가구 제조업"),
    ("14A", "기타제품 제조업"),
    ("210", "서적, 잡지 및 기타 인쇄물 출판업"),
    ("211", "영화, 비디오물, 방송프로그램 제작 및 배급업"),
    ("212", "음악 및 오디오물 출판 및 원판 녹음업"),
    ("213", "방송업"),
    ("220", "소프트웨어개발 및 공급업"),
    ("221", "전기통신업"),
    ("222", "컴퓨터 프로그래밍, 시스템 통합 및 관리업"),
    ("223", "정보서비스업"),
    ("230", "연구개발업"),
    ("231", "법무ㆍ회계ㆍ건축 서비스"),
    ("232", "광고대행업 및 전시광고업"),
    ("233", "시장조사 및 여론조사업"),
    ("234", "경영컨설팅업"),
    ("235", "건축기술, 엔지니어링 및 기타 과학기술 서비스업"),
    ("236", "기타 전문, 과학 및 기술 서비스업"),
    ("237", "사업지원 서비스업"),
]

# 업종구분코드 Level 2 (중분류) 주요 항목
level2_codes = {
    "C10": "식료품 제조업",
    "C11": "음료 제조업",
    "C12": "담배 제조업",
    "C13": "섬유제품 제조업; 의복 제외",
    "C14": "의복, 의복 액세서리 및 모피제품 제조업",
    "C15": "가죽, 가방 및 신발 제조업",
    "C16": "목재 및 나무제품 제조업; 가구 제외",
    "C17": "펄프, 종이 및 종이제품 제조업",
    "C18": "인쇄 및 기록매체 복제업",
    "C19": "코크스, 연탄 및 석유정제품 제조업",
    "C20": "화학 물질 및 화학제품 제조업; 의약품 제외",
    "C21": "의료용 물질 및 의약품 제조업",
    "C22": "고무 및 플라스틱제품 제조업",
    "C23": "비금속 광물제품 제조업",
    "C24": "1차 금속 제조업",
    "C25": "금속 가공제품 제조업; 기계 및 가구 제외",
    "C26": "전자 부품, 컴퓨터, 영상, 음향 및 통신장비 제조업",
    "C27": "의료, 정밀, 광학 기기 및 시계 제조업",
    "C28": "전기장비 제조업",
    "C29": "기타 기계 및 장비 제조업",
    "C30": "자동차 및 트레일러 제조업",
    "C31": "기타 운송장비 제조업",
    "C32": "가구 제조업",
    "C33": "기타 제품 제조업",
    "J58": "출판업",
    "J59": "영상ㆍ오디오 기록물 제작 및 배급업",
    "J60": "방송업",
    "J61": "우편 및 통신업",
    "J62": "컴퓨터 프로그래밍, 시스템 통합 및 관리업",
    "J63": "정보서비스업",
    "M70": "연구개발업",
    "M71": "전문 서비스업",
    "M72": "건축 기술, 엔지니어링 및 기타 과학기술 서비스업",
    "M73": "기타 전문, 과학 및 기술 서비스업",
    "N75": "사업 지원 서비스업",
}

# Level 3 (소분류) 일부
level3_codes = {
    "C311": "선박 및 보트 건조업",
    "C313": "항공기, 우주선 및 부품 제조업",
    "J620": "소프트웨어 개발 및 공급업",
}

print("=" * 80)
print("theme_cd와 업종구분코드 Level 2 (중분류) 비교")
print("=" * 80)

matched_level2 = []
matched_level3 = []
not_matched = []

for theme_code, theme_name in theme_items:
    # Level 2에서 찾기
    found = False
    for industry_code, industry_name in level2_codes.items():
        # 이름 정규화 (공백, 특수문자 제거)
        theme_normalized = theme_name.replace(' ', '').replace('ㆍ', '·').replace('_', '').replace(';', '').lower()
        industry_normalized = industry_name.replace(' ', '').replace('ㆍ', '·').replace(';', '').lower()
        
        # 정확히 일치하거나, theme_name이 industry_name에 포함되거나
        if (theme_normalized == industry_normalized or 
            theme_normalized in industry_normalized or 
            industry_normalized in theme_normalized):
            matched_level2.append((theme_code, theme_name, industry_code, industry_name))
            found = True
            break
    
    # Level 3에서 찾기
    if not found:
        for industry_code, industry_name in level3_codes.items():
            theme_normalized = theme_name.replace(' ', '').replace('ㆍ', '·').replace('_', '').lower()
            industry_normalized = industry_name.replace(' ', '').replace('ㆍ', '·').lower()
            
            if (theme_normalized == industry_normalized or 
                theme_normalized in industry_normalized or 
                industry_normalized in theme_normalized):
                matched_level3.append((theme_code, theme_name, industry_code, industry_name))
                found = True
                break
    
    if not found:
        not_matched.append((theme_code, theme_name))

print(f"\nLevel 2 (중분류) 매칭: {len(matched_level2)}개")
print(f"Level 3 (소분류) 매칭: {len(matched_level3)}개")
print(f"매칭되지 않음: {len(not_matched)}개\n")

print("\n" + "=" * 80)
print("Level 2 (중분류) 매칭 결과")
print("=" * 80)
for theme_code, theme_name, industry_code, industry_name in matched_level2:
    print(f"theme_cd={theme_code}: {theme_name}")
    print(f"  → {industry_code}: {industry_name}")

print("\n" + "=" * 80)
print("Level 3 (소분류) 매칭 결과")
print("=" * 80)
for theme_code, theme_name, industry_code, industry_name in matched_level3:
    print(f"theme_cd={theme_code}: {theme_name}")
    print(f"  → {industry_code}: {industry_name}")

print("\n" + "=" * 80)
print("매칭되지 않은 항목 (수동 확인 필요)")
print("=" * 80)
for theme_code, theme_name in not_matched:
    print(f"theme_cd={theme_code}: {theme_name}")

print("\n" + "=" * 80)
print("결론")
print("=" * 80)
print(f"총 {len(theme_items)}개 중 {len(matched_level2) + len(matched_level3)}개가 업종구분코드와 매칭됨")
print(f"매칭률: {(len(matched_level2) + len(matched_level3)) / len(theme_items) * 100:.1f}%")
print(f"\n주로 Level 2 (중분류)와 매칭: {len(matched_level2)}개")
print(f"일부 Level 3 (소분류)와 매칭: {len(matched_level3)}개")

