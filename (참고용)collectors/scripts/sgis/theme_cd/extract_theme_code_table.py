"""PDF에서 테마 코드표 추출"""

import pdfplumber
from pathlib import Path

pdf_path = Path("docs/sources/sgis/SGIS_OpenAPI_정의서.pdf")

if not pdf_path.exists():
    print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    exit(1)

print("=" * 80)
print("테마 코드표 추출")
print("=" * 80)

# 테마 코드표가 있을 가능성이 있는 페이지들
# 이전 검색에서 35, 47, 53, 58, 61, 64, 67, 70 페이지에 테마 코드표가 언급됨
target_pages = [35, 47, 53, 58, 61, 64, 67, 70]

try:
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in target_pages:
            if page_num > len(pdf.pages):
                continue
                
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            
            if text and '테마 코드표' in text:
                print(f"\n{'='*80}")
                print(f"페이지 {page_num}")
                print(f"{'='*80}\n")
                
                # 테이블 추출
                tables = page.extract_tables()
                if tables:
                    print(f"테이블 {len(tables)}개 발견:")
                    for idx, table in enumerate(tables):
                        if table and len(table) > 0:
                            # 테마 코드표인지 확인 (대분류, 소분류 같은 키워드가 있는지)
                            table_text = ' '.join([' '.join(str(cell) if cell else "" for cell in row) for row in table[:5]])
                            if '대분류' in table_text or '소분류' in table_text or '테마' in table_text:
                                print(f"\n--- 테이블 {idx + 1} (테마 코드표로 추정) ---")
                                for row in table:
                                    if row and any(cell for cell in row):
                                        print(" | ".join(str(cell) if cell else "" for cell in row))
                                print()
                
                # 텍스트에서 테마 코드 관련 내용 추출
                lines = text.split('\n')
                theme_section = False
                theme_lines = []
                
                for line in lines:
                    if '테마 코드표' in line or '대분류' in line:
                        theme_section = True
                    if theme_section:
                        theme_lines.append(line)
                        if len(theme_lines) > 30:  # 최대 30줄
                            break
                
                if theme_lines:
                    print("--- 텍스트 내용 ---")
                    print('\n'.join(theme_lines[:30]))
                    print()

except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()

