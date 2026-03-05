"""
PDF 파일을 컴퓨터가 읽을 수 있는지 테스트하는 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_pdf_with_pymupdf(pdf_path):
    """PyMuPDF로 PDF 읽기 테스트"""
    try:
        import fitz  # PyMuPDF
        
        print("=" * 60)
        print("PyMuPDF로 테스트")
        print("=" * 60)
        
        doc = fitz.open(str(pdf_path))
        
        print(f"✓ PDF 파일 열기 성공")
        print(f"  총 페이지 수: {len(doc)}")
        
        # 첫 페이지 읽기
        page = doc[0]
        text = page.get_text()
        
        print(f"  첫 페이지 텍스트 길이: {len(text)} 문자")
        print(f"  첫 페이지 텍스트 미리보기 (처음 200자):")
        print(f"  {text[:200]}...")
        
        # 전체 텍스트 길이 확인
        total_text = ""
        for page_num in range(min(5, len(doc))):  # 처음 5페이지만
            total_text += doc[page_num].get_text()
        
        print(f"  처음 5페이지 총 텍스트 길이: {len(total_text)} 문자")
        
        doc.close()
        return True
        
    except ImportError:
        print("PyMuPDF가 설치되지 않았습니다.")
        return False
    except Exception as e:
        print(f"오류: {e}")
        return False


def test_pdf_with_pdfplumber(pdf_path):
    """pdfplumber로 PDF 읽기 테스트"""
    try:
        import pdfplumber
        
        print("\n" + "=" * 60)
        print("pdfplumber로 테스트")
        print("=" * 60)
        
        with pdfplumber.open(str(pdf_path)) as pdf:
            print(f"✓ PDF 파일 열기 성공")
            print(f"  총 페이지 수: {len(pdf.pages)}")
            
            # 첫 페이지 읽기
            page = pdf.pages[0]
            text = page.extract_text()
            
            if text:
                print(f"  첫 페이지 텍스트 길이: {len(text)} 문자")
                print(f"  첫 페이지 텍스트 미리보기 (처음 200자):")
                print(f"  {text[:200]}...")
            else:
                print("  첫 페이지에서 텍스트를 추출할 수 없습니다.")
            
            # 전체 텍스트 길이 확인
            total_text = ""
            for page_num in range(min(5, len(pdf.pages))):  # 처음 5페이지만
                page_text = pdf.pages[page_num].extract_text()
                if page_text:
                    total_text += page_text
            
            print(f"  처음 5페이지 총 텍스트 길이: {len(total_text)} 문자")
        
        return True
        
    except ImportError:
        print("pdfplumber가 설치되지 않았습니다.")
        return False
    except Exception as e:
        print(f"오류: {e}")
        return False


def analyze_pdf_structure(pdf_path):
    """PDF 구조 분석"""
    try:
        import fitz  # PyMuPDF
        
        print("\n" + "=" * 60)
        print("PDF 구조 분석")
        print("=" * 60)
        
        doc = fitz.open(str(pdf_path))
        
        print(f"파일명: {pdf_path.name}")
        print(f"파일 크기: {pdf_path.stat().st_size:,} bytes")
        print(f"총 페이지 수: {len(doc)}")
        
        # 메타데이터 확인
        metadata = doc.metadata
        print(f"\n메타데이터:")
        for key, value in metadata.items():
            if value:
                print(f"  {key}: {value}")
        
        # 각 페이지별 텍스트 길이 확인
        print(f"\n페이지별 텍스트 길이 (처음 10페이지):")
        for page_num in range(min(10, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            print(f"  페이지 {page_num + 1}: {len(text)} 문자")
        
        # 이미지 확인
        image_count = 0
        for page_num in range(min(5, len(doc))):
            page = doc[page_num]
            image_list = page.get_images()
            image_count += len(image_list)
        
        print(f"\n처음 5페이지 이미지 수: {image_count}")
        
        # 폰트 확인
        fonts = set()
        for page_num in range(min(5, len(doc))):
            page = doc[page_num]
            font_list = page.get_fonts()
            for font in font_list:
                fonts.add(font.get('name', 'Unknown'))
        
        print(f"\n처음 5페이지 사용된 폰트:")
        for font in sorted(fonts):
            print(f"  - {font}")
        
        doc.close()
        
        return True
        
    except Exception as e:
        print(f"구조 분석 실패: {e}")
        return False


def main():
    """메인 함수"""
    pdf_file = project_root / "docs" / "sources" / "sbiz" / "raw" / "소상공인시장진흥공단_상가(상권)정보_OpenApi 활용가이드.pdf"
    
    if not pdf_file.exists():
        print(f"파일을 찾을 수 없습니다: {pdf_file}")
        return
    
    print(f"PDF 파일 읽기 테스트")
    print(f"파일: {pdf_file.name}")
    print()
    
    # 각 라이브러리로 테스트
    pymupdf_ok = test_pdf_with_pymupdf(pdf_file)
    pdfplumber_ok = test_pdf_with_pdfplumber(pdf_file)
    
    # PDF 구조 분석
    analyze_pdf_structure(pdf_file)
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    
    if pymupdf_ok:
        print("✓ PyMuPDF: PDF를 읽을 수 있습니다")
    else:
        print("✗ PyMuPDF: PDF를 읽을 수 없습니다")
    
    if pdfplumber_ok:
        print("✓ pdfplumber: PDF를 읽을 수 있습니다")
    else:
        print("✗ pdfplumber: PDF를 읽을 수 없습니다")
    
    if pymupdf_ok or pdfplumber_ok:
        print("\n✅ 결론: 이 PDF 파일은 컴퓨터가 읽을 수 있습니다!")
        print("   텍스트 추출, 마크다운 변환, 데이터 분석 등이 가능합니다.")
    else:
        print("\n❌ 결론: 현재 설치된 라이브러리로는 이 PDF를 읽을 수 없습니다.")


if __name__ == "__main__":
    main()
