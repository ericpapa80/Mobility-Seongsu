#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV 파일에 theme_cd 기반 분류 정보 추가 스크립트
"""

import csv
import os
from datetime import datetime

# theme_cd 매핑 딕셔너리
# {theme_cd: (소분류_코드명, 대분류_코드명, 대분류_코드)}
THEME_MAPPING = {
    # 첨단기술(11)
    "110": ("의료용 물질 및 의약품 제조업", "첨단기술", "11"),
    "111": ("전자부품, 컴퓨터, 영상, 음향 및 통신장비 제조업", "첨단기술", "11"),
    "112": ("의료, 정밀, 광학기기 및 시계제조업", "첨단기술", "11"),
    "113": ("항공기, 우주선 및 부품 제조업", "첨단기술", "11"),
    
    # 고기술(12)
    "120": ("화학물질 및 화학제품 제조업", "고기술", "12"),
    "121": ("전기장비 제조업", "고기술", "12"),
    "122": ("기타 기계 및 장비 제조업", "고기술", "12"),
    "123": ("자동차 및 트레일러 제조업", "고기술", "12"),
    "124": ("기타 운송장비 제조업", "고기술", "12"),
    
    # 중기술(13)
    "130": ("코크스, 연탄 및 석유정제품 제조업", "중기술", "13"),
    "131": ("고무제품 및 플라스틱 제조업", "중기술", "13"),
    "132": ("비금속 광물제품 제조업", "중기술", "13"),
    "133": ("1차 금속 제조업", "중기술", "13"),
    "134": ("금속가공제품 제조업", "중기술", "13"),
    "135": ("선박 및 보트 건조업", "중기술", "13"),
    
    # 저기술(14)
    "140": ("식료품 제조업", "저기술", "14"),
    "141": ("음료 제조업", "저기술", "14"),
    "142": ("담배 제조업", "저기술", "14"),
    "143": ("섬유제품 제조업_의복복 제외", "저기술", "14"),
    "144": ("의복, 의복액세서리 및 모피제품 제조업", "저기술", "14"),
    "145": ("가죽 가방 및 신발 제조업", "저기술", "14"),
    "146": ("목재 및 나무제품 제조업", "저기술", "14"),
    "147": ("펄프, 종이 및 종이제품 제조업", "저기술", "14"),
    "148": ("인쇄 및 기록매체 복제업", "저기술", "14"),
    "149": ("가구 제조업", "저기술", "14"),
    "14A": ("기타제품 제조업", "저기술", "14"),
    
    # 창의/디지털(21)
    "210": ("서적, 잡지 및 기타 인쇄물 출판업", "창의 및 디지털", "21"),
    "211": ("영화, 비디오물, 방송프로그램 제작 및 배급업", "창의 및 디지털", "21"),
    "212": ("음악 및 오디오물 출판 및 원판 녹음업", "창의 및 디지털", "21"),
    "213": ("방송업", "창의 및 디지털", "21"),
    
    # ICT(22)
    "220": ("소프트웨어개발 및 공급업", "ICT", "22"),
    "221": ("전기통신업", "ICT", "22"),
    "222": ("컴퓨터 프로그래밍, 시스템 통합 및 관리업", "ICT", "22"),
    "223": ("정보서비스업", "ICT", "22"),
    
    # 전문서비스(23)
    "230": ("연구개발업", "전문서비스", "23"),
    "231": ("법무ㆍ회계ㆍ건축 서비스", "전문서비스", "23"),
    "232": ("광고대행업 및 전시광고업", "전문서비스", "23"),
    "233": ("시장조사 및 여론조사업", "전문서비스", "23"),
    "234": ("경영컨설팅업", "전문서비스", "23"),
    "235": ("건축기술, 엔지니어링 및 기타 과학기술 서비스업", "전문서비스", "23"),
    "236": ("기타 전문, 과학 및 기술 서비스업", "전문서비스", "23"),
    "237": ("사업지원 서비스업", "전문서비스", "23"),
}


def process_csv(input_file, output_file):
    """
    CSV 파일을 읽어서 theme_cd 기반 분류 정보를 추가하고 저장
    """
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    
    # 입력 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        # 새로운 컬럼 추가
        new_fieldnames = list(fieldnames) + ['소분류_코드명', '대분류_코드명', '대분류_코드']
        
        rows = []
        missing_codes = set()
        
        for row in reader:
            theme_cd = row.get('theme_cd', '').strip().strip('"')
            
            if theme_cd in THEME_MAPPING:
                소분류_코드명, 대분류_코드명, 대분류_코드 = THEME_MAPPING[theme_cd]
                row['소분류_코드명'] = 소분류_코드명
                row['대분류_코드명'] = 대분류_코드명
                row['대분류_코드'] = 대분류_코드
            else:
                # 매핑되지 않은 코드
                missing_codes.add(theme_cd)
                row['소분류_코드명'] = ''
                row['대분류_코드명'] = ''
                row['대분류_코드'] = ''
            
            rows.append(row)
    
    # 매핑되지 않은 코드가 있으면 경고 출력
    if missing_codes:
        print(f"\n[경고] 매핑되지 않은 theme_cd 코드가 있습니다: {sorted(missing_codes)}")
    
    # 출력 파일 저장
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n[완료] 처리 완료: {len(rows)}개 행 처리")
    print(f"   - 소분류_코드명, 대분류_코드명, 대분류_코드 컬럼이 추가되었습니다.")


if __name__ == '__main__':
    # 파일 경로 설정
    input_file = r'collectors\data\raw\sgis\merged\sgis_technical_biz_merged_2016_2023_seongsu_20251201_225930.csv'
    output_file = r'collectors\data\raw\sgis\merged\sgis_technical_biz_merged_2016_2023_seongsu_with_classification.csv'
    
    # 절대 경로로 변환
    # 스크립트 위치: collectors/scripts/add_theme_classification.py
    # 프로젝트 루트: framework/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    collectors_dir = os.path.dirname(script_dir)  # collectors/
    project_root = os.path.dirname(collectors_dir)  # framework/
    
    input_path = os.path.join(project_root, input_file)
    output_path = os.path.join(project_root, output_file)
    
    # 파일 존재 확인
    if not os.path.exists(input_path):
        print(f"[오류] 입력 파일을 찾을 수 없습니다: {input_path}")
        exit(1)
    
    # 처리 실행
    process_csv(input_path, output_path)

