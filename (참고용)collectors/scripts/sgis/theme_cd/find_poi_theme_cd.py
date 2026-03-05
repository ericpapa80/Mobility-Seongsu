"""PDF에서 getPoiCompanyDensity API의 theme_cd 정보 찾기"""

import pdfplumber
import re
from pathlib import Path

pdf_path = Path("docs/sources/sgis/SGIS_OpenAPI_정의서.pdf")

if not pdf_path.exists():
    print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    exit(1)

print("=" * 80)
print("getPoiCompanyDensity 또는 POI 관련 theme_cd 정보 검색")
print("=" * 80)

keywords = [
    "getPoiCompanyDensity",
    "PoiCompanyDensity",
    "POI",
    "poi",
    "기술업종 통계지도"
]

try:
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"총 페이지 수: {total_pages}\n")
        
        found_pages = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            
            if text:
                # 키워드 검색
                found = False
                matched_keywords = []
                
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        found = True
                        matched_keywords.append(keyword)
                
                if found:
                    found_pages.append((page_num, matched_keywords, text))
        
        print(f"관련 페이지 {len(found_pages)}개 발견\n")
        
        for page_num, keywords, text in found_pages:
            print(f"\n{'='*80}")
            print(f"페이지 {page_num} - 키워드: {', '.join(keywords)}")
            print(f"{'='*80}\n")
            
            # theme_cd 관련 부분 추출
            lines = text.split('\n')
            relevant_lines = []
            
            for i, line in enumerate(lines):
                if any(kw.lower() in line.lower() for kw in keywords) or 'theme_cd' in line.lower():
                    # 주변 컨텍스트 포함
                    start = max(0, i - 2)
                    end = min(len(lines), i + 15)
                    context = '\n'.join(lines[start:end])
                    relevant_lines.append(context)
            
            # 중복 제거하고 출력
            seen = set()
            for context in relevant_lines[:5]:  # 처음 5개만
                if context not in seen:
                    seen.add(context)
                    print(context)
                    print("\n" + "-"*80 + "\n")
            
            # 테이블도 확인
            tables = page.extract_tables()
            if tables:
                print(f"테이블 {len(tables)}개 발견:")
                for idx, table in enumerate(tables):
                    if table and len(table) > 0:
                        # theme_cd 관련 테이블인지 확인
                        table_text = ' '.join([' '.join(str(cell) if cell else "" for cell in row) for row in table[:3]])
                        if 'theme' in table_text.lower() or '테마' in table_text:
                            print(f"\n--- 테이블 {idx + 1} (theme_cd 관련) ---")
                            for row in table[:20]:  # 처음 20행
                                if row:
                                    print(" | ".join(str(cell) if cell else "" for cell in row))
                            if len(table) > 20:
                                print(f"... (총 {len(table)}행)")

except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()

