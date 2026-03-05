"""
PDF 파일을 마크다운(.md) 파일로 변환하는 스크립트
여러 라이브러리를 시도하여 최상의 결과를 얻습니다.
"""

import sys
from pathlib import Path
import re
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def convert_pdf_to_md_pymupdf(pdf_path, output_path):
    """
    PyMuPDF (fitz)를 사용하여 PDF를 마크다운으로 변환합니다.
    """
    try:
        import fitz  # PyMuPDF
        
        print("PyMuPDF를 사용하여 변환합니다...")
        
        doc = fitz.open(str(pdf_path))
        
        md_content = f"# {pdf_path.stem}\n\n"
        md_content += f"*변환 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        md_content += "---\n\n"
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if text.strip():
                # 페이지 번호 추가 (선택사항)
                if page_num > 0:
                    md_content += f"\n\n---\n\n## 페이지 {page_num + 1}\n\n"
                
                # 텍스트 정리 및 마크다운 형식으로 변환
                processed_text = process_text_for_markdown(text)
                md_content += processed_text
        
        doc.close()
        
        # 마크다운 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✓ 성공: {output_path.name}")
        return True
        
    except ImportError:
        print("PyMuPDF가 설치되지 않았습니다.")
        return False
    except Exception as e:
        print(f"PyMuPDF 변환 실패: {e}")
        return False


def convert_pdf_to_md_pdfplumber(pdf_path, output_path):
    """
    pdfplumber를 사용하여 PDF를 마크다운으로 변환합니다.
    """
    try:
        import pdfplumber
        
        print("pdfplumber를 사용하여 변환합니다...")
        
        md_content = f"# {pdf_path.stem}\n\n"
        md_content += f"*변환 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        md_content += "---\n\n"
        
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                
                if text and text.strip():
                    # 페이지 번호 추가 (선택사항)
                    if page_num > 0:
                        md_content += f"\n\n---\n\n## 페이지 {page_num + 1}\n\n"
                    
                    # 텍스트 정리 및 마크다운 형식으로 변환
                    processed_text = process_text_for_markdown(text)
                    md_content += processed_text
        
        # 마크다운 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✓ 성공: {output_path.name}")
        return True
        
    except ImportError:
        print("pdfplumber가 설치되지 않았습니다.")
        return False
    except Exception as e:
        print(f"pdfplumber 변환 실패: {e}")
        return False


def convert_pdf_to_md_pypdf2(pdf_path, output_path):
    """
    PyPDF2를 사용하여 PDF를 마크다운으로 변환합니다.
    """
    try:
        from PyPDF2 import PdfReader
        
        print("PyPDF2를 사용하여 변환합니다...")
        
        reader = PdfReader(str(pdf_path))
        
        md_content = f"# {pdf_path.stem}\n\n"
        md_content += f"*변환 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        md_content += "---\n\n"
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            
            if text and text.strip():
                # 페이지 번호 추가 (선택사항)
                if page_num > 0:
                    md_content += f"\n\n---\n\n## 페이지 {page_num + 1}\n\n"
                
                # 텍스트 정리 및 마크다운 형식으로 변환
                processed_text = process_text_for_markdown(text)
                md_content += processed_text
        
        # 마크다운 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✓ 성공: {output_path.name}")
        return True
        
    except ImportError:
        print("PyPDF2가 설치되지 않았습니다.")
        return False
    except Exception as e:
        print(f"PyPDF2 변환 실패: {e}")
        return False


def process_text_for_markdown(text):
    """
    추출된 텍스트를 마크다운 형식으로 정리합니다.
    """
    lines = text.split('\n')
    processed_lines = []
    prev_line_was_heading = False
    
    for line in lines:
        line = line.strip()
        
        if not line:
            if processed_lines and processed_lines[-1] != '':
                processed_lines.append('')
            continue
        
        # 제목 패턴 감지
        # 1. 번호로 시작하는 제목 (예: "1. 서비스 개요", "1.1. 개요")
        if re.match(r'^\d+[\.\)]\s+', line) or re.match(r'^\d+\.\d+[\.\)]?\s+', line):
            if not prev_line_was_heading and processed_lines:
                processed_lines.append('')
            line = re.sub(r'^(\d+[\.\)])\s+', r'## \1 ', line)
            line = re.sub(r'^(\d+\.\d+[\.\)]?)\s+', r'### \1 ', line)
            processed_lines.append(line)
            processed_lines.append('')
            prev_line_was_heading = True
            continue
        
        # 2. 한글 제목 패턴 (예: "가. 배경", "나. 필요성")
        if re.match(r'^[가-힣]\.\s+', line):
            if not prev_line_was_heading and processed_lines:
                processed_lines.append('')
            line = re.sub(r'^([가-힣]\.)\s+', r'### \1 ', line)
            processed_lines.append(line)
            processed_lines.append('')
            prev_line_was_heading = True
            continue
        
        # 3. 콜론으로 끝나는 줄 (제목일 가능성)
        if re.match(r'^[가-힣\s]+:$', line) and len(line) < 50:
            if not prev_line_was_heading and processed_lines:
                processed_lines.append('')
            processed_lines.append(f"## {line}")
            processed_lines.append('')
            prev_line_was_heading = True
            continue
        
        # 4. 대문자로 시작하고 짧은 줄 (제목일 가능성)
        if line.isupper() and len(line) < 50 and not line.isdigit():
            if not prev_line_was_heading and processed_lines:
                processed_lines.append('')
            processed_lines.append(f"## {line}")
            processed_lines.append('')
            prev_line_was_heading = True
            continue
        
        # 일반 텍스트
        processed_lines.append(line)
        prev_line_was_heading = False
    
    # 연속된 빈 줄 제거
    result = []
    prev_empty = False
    for line in processed_lines:
        if line == '':
            if not prev_empty:
                result.append('')
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    
    return '\n'.join(result)


def main():
    """메인 함수"""
    pdf_file = project_root / "docs" / "sources" / "sbiz" / "raw" / "소상공인시장진흥공단_상가(상권)정보_OpenApi 활용가이드.pdf"
    
    if not pdf_file.exists():
        print(f"파일을 찾을 수 없습니다: {pdf_file}")
        return
    
    output_file = project_root / "docs" / "sources" / "sbiz" / "converted" / f"{pdf_file.stem}.md"
    
    print(f"PDF 파일 변환: {pdf_file.name}")
    print(f"출력 파일: {output_file.name}")
    print("-" * 60)
    
    # 여러 방법 시도 (우선순위 순서)
    success = False
    
    # 방법 1: PyMuPDF (가장 정확하고 빠름)
    if not success:
        success = convert_pdf_to_md_pymupdf(pdf_file, output_file)
    
    # 방법 2: pdfplumber (표와 레이아웃 보존에 좋음)
    if not success:
        success = convert_pdf_to_md_pdfplumber(pdf_file, output_file)
    
    # 방법 3: PyPDF2 (기본적인 텍스트 추출)
    if not success:
        success = convert_pdf_to_md_pypdf2(pdf_file, output_file)
    
    if not success:
        print("\n⚠ 모든 변환 방법이 실패했습니다.")
        print("\n다음 라이브러리를 설치해주세요:")
        print("  - PyMuPDF: pip install PyMuPDF")
        print("  - pdfplumber: pip install pdfplumber")
        print("  - PyPDF2: pip install PyPDF2")
    else:
        print("-" * 60)
        print(f"✓ 변환 완료: {output_file}")
        
        # 파일 크기 확인
        file_size = output_file.stat().st_size
        print(f"  파일 크기: {file_size:,} bytes")


if __name__ == "__main__":
    main()
