"""PDF에서 기술업종 API의 theme_cd 정보 상세 추출"""

import pdfplumber
import re
from pathlib import Path

pdf_path = Path("docs/sources/sgis/SGIS_OpenAPI_정의서.pdf")

if not pdf_path.exists():
    print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    exit(1)

print("=" * 80)
print("기술업종 API 관련 theme_cd 정보 추출")
print("=" * 80)

# 기술업종 관련 페이지 범위 (109-120 페이지 정도)
target_pages = list(range(109, 121))

try:
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in target_pages:
            if page_num > len(pdf.pages):
                continue
                
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            
            if text and ('기술업종' in text or 'technicalBiz' in text or 'theme_cd' in text.lower()):
                print(f"\n{'='*80}")
                print(f"페이지 {page_num}")
                print(f"{'='*80}\n")
                
                # 전체 텍스트 출력 (긴 경우 일부만)
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if any(keyword in line for keyword in ['theme_cd', '테마코드', '기술업종', 'technicalBiz', 'techbiz_cd']):
                        # 주변 컨텍스트 포함
                        start = max(0, i - 3)
                        end = min(len(lines), i + 10)
                        context = '\n'.join(lines[start:end])
                        print(context)
                        print("\n" + "-"*80 + "\n")
                        break
                
                # 테이블 추출 시도
                tables = page.extract_tables()
                if tables:
                    print(f"테이블 {len(tables)}개 발견:")
                    for idx, table in enumerate(tables):
                        if table and len(table) > 0:
                            print(f"\n--- 테이블 {idx + 1} ---")
                            for row in table[:10]:  # 처음 10행만
                                if row:
                                    print(" | ".join(str(cell) if cell else "" for cell in row))
                            if len(table) > 10:
                                print(f"... (총 {len(table)}행)")
                
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()

