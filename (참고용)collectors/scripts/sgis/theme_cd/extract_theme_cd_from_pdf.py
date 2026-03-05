"""PDF에서 theme_cd 관련 정보 추출 스크립트"""

import pdfplumber
import re
from pathlib import Path

pdf_path = Path("docs/sources/sgis/SGIS_OpenAPI_정의서.pdf")

if not pdf_path.exists():
    print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    exit(1)

print(f"PDF 파일 읽는 중: {pdf_path}")
print("=" * 80)

# theme_cd 관련 키워드
keywords = [
    "theme_cd",
    "theme_cd",
    "테마코드",
    "테마 코드",
    "theme code",
    "기술업종",
    "technicalBiz"
]

found_sections = []
page_numbers = []

try:
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"총 페이지 수: {total_pages}\n")
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            
            if text:
                # 키워드 검색
                found_keywords = []
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        found_keywords.append(keyword)
                
                if found_keywords:
                    page_numbers.append(page_num)
                    # theme_cd 패턴 찾기
                    theme_cd_patterns = re.findall(r'theme[_\-]?cd\s*[:=]?\s*[\d\w]+', text, re.IGNORECASE)
                    theme_cd_patterns_kr = re.findall(r'테마\s*코드\s*[:=]?\s*[\d\w]+', text)
                    
                    # 주변 텍스트 추출 (키워드 주변 200자)
                    context_lines = []
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        for keyword in found_keywords:
                            if keyword.lower() in line.lower():
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                context = '\n'.join(lines[start:end])
                                context_lines.append(context)
                                break
                    
                    found_sections.append({
                        'page': page_num,
                        'keywords': found_keywords,
                        'theme_cd_patterns': theme_cd_patterns + theme_cd_patterns_kr,
                        'context': context_lines[:3]  # 처음 3개만
                    })
        
        # 결과 출력
        print(f"theme_cd 관련 내용이 발견된 페이지: {len(page_numbers)}개\n")
        
        if found_sections:
            for section in found_sections:
                print(f"\n{'='*80}")
                print(f"페이지 {section['page']}")
                print(f"발견된 키워드: {', '.join(section['keywords'])}")
                if section['theme_cd_patterns']:
                    print(f"theme_cd 패턴: {section['theme_cd_patterns']}")
                print(f"\n주변 텍스트:")
                for i, context in enumerate(section['context'], 1):
                    print(f"\n--- 컨텍스트 {i} ---")
                    print(context[:500])  # 처음 500자만
        else:
            print("theme_cd 관련 내용을 찾을 수 없습니다.")
            print("\n전체 텍스트에서 'theme' 또는 '테마' 검색 중...")
            
            # 전체 검색
            all_theme_mentions = []
            with pdfplumber.open(pdf_path) as pdf2:
                for page_num, page in enumerate(pdf2.pages, 1):
                    text = page.extract_text()
                    if text and ('theme' in text.lower() or '테마' in text):
                        lines = text.split('\n')
                        for line in lines:
                            if 'theme' in line.lower() or '테마' in line:
                                all_theme_mentions.append((page_num, line.strip()))
            
            if all_theme_mentions:
                print(f"\n'theme' 또는 '테마'가 포함된 줄 ({len(all_theme_mentions)}개):")
                for page, line in all_theme_mentions[:20]:  # 처음 20개만
                    print(f"  페이지 {page}: {line[:100]}")
            else:
                print("'theme' 또는 '테마' 관련 내용을 찾을 수 없습니다.")

except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()

