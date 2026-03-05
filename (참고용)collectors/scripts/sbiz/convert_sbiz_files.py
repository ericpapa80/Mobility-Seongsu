"""
소상공인시장진흥공단 문서 파일 변환 스크립트
.hwp 파일을 텍스트/마크다운으로, .xlsx 파일을 CSV/JSON으로 변환합니다.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def convert_hwp_to_text(hwp_path, output_dir):
    """
    .hwp 파일을 텍스트 파일로 변환합니다.
    여러 방법을 시도합니다.
    """
    output_path = output_dir / f"{hwp_path.stem}.txt"
    markdown_path = output_dir / f"{hwp_path.stem}.md"
    
    print(f"변환 중: {hwp_path.name} -> {output_path.name}")
    
    # 방법 1: pyhwp 라이브러리 시도
    try:
        import pyhwp
        from pyhwp import hwp5
        
        with open(hwp_path, 'rb') as f:
            hwp = hwp5.HWP5File(f)
            text_content = []
            
            for section in hwp.bodytext.sections:
                for paragraph in section.paragraphs:
                    for char in paragraph.chars:
                        if hasattr(char, 'text'):
                            text_content.append(char.text)
            
            content = ''.join(text_content)
            
            # 텍스트 파일로 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 마크다운 파일로도 저장
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(f"# {hwp_path.stem}\n\n")
                f.write(content)
            
            print(f"✓ 성공: {output_path.name}, {markdown_path.name}")
            return True
            
    except ImportError:
        print("pyhwp 라이브러리가 설치되지 않았습니다. 다른 방법을 시도합니다...")
    except Exception as e:
        print(f"pyhwp로 변환 실패: {e}")
    
    # 방법 2: hwp5 라이브러리 시도
    try:
        from hwp5 import plat
        from hwp5.proc import rest_to_docopt
        from hwp5.dataio import ParseError
        
        # hwp5를 사용한 변환
        with open(hwp_path, 'rb') as f:
            hwp5_file = plat.HWP5File(f)
            # 텍스트 추출 시도
            text_content = []
            # 간단한 텍스트 추출 로직
            # (실제 구현은 hwp5의 구조에 따라 달라질 수 있음)
            
    except ImportError:
        print("hwp5 라이브러리가 설치되지 않았습니다.")
    except Exception as e:
        print(f"hwp5로 변환 실패: {e}")
    
    # 방법 3: Windows COM을 통한 한글 프로그램 사용 (Windows 전용)
    try:
        import win32com.client
        import pythoncom
        
        print("Windows COM을 통한 한글 프로그램 변환을 시도합니다...")
        
        # 한글 프로그램 실행
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        hwp.XHwpWindows.Item(0).Visible = False  # 백그라운드 실행
        
        # 파일 열기
        hwp.Open(hwp_path)
        
        # 텍스트 추출
        text_content = hwp.GetText()
        
        # 파일 닫기
        hwp.Quit()
        
        # 텍스트 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # 마크다운 파일로도 저장
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(f"# {hwp_path.stem}\n\n")
            f.write(text_content.replace('\n', '\n\n'))
        
        print(f"✓ 성공: {output_path.name}, {markdown_path.name}")
        return True
        
    except ImportError:
        print("pywin32 라이브러리가 설치되지 않았습니다. 다른 방법을 시도합니다...")
    except Exception as e:
        print(f"Windows COM으로 변환 실패: {e}")
    
    # 방법 4: olefile을 사용한 기본 변환 시도
    try:
        import olefile
        
        if olefile.isOleFile(hwp_path):
            ole = olefile.OleFileIO(hwp_path)
            print("OLE 파일 형식 감지됨. 파일 구조를 분석합니다...")
            
            # 스트림 목록 확인
            streams = ole.listdir()
            
            text_content = f"원본 파일: {hwp_path.name}\n"
            text_content += f"변환 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_content += f"\n파일 구조:\n"
            for stream in streams:
                text_content += f"  - {stream}\n"
            text_content += "\n주의: 이 파일은 자동 변환되었으며, 내용이 제한적일 수 있습니다.\n"
            text_content += "정확한 내용을 보려면 한글 프로그램으로 직접 열어보세요.\n"
            text_content += "\n변환 방법:\n"
            text_content += "1. 한글 프로그램으로 파일 열기\n"
            text_content += "2. '파일' -> '다른 이름으로 저장' -> '텍스트 파일' 선택\n"
            text_content += "3. 또는 '파일' -> '인쇄' -> 'PDF로 저장' 선택\n"
            
            ole.close()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            print(f"⚠ 부분 변환 완료: {output_path.name} (내용이 제한적일 수 있음)")
            return True
            
    except ImportError:
        print("olefile 라이브러리가 설치되지 않았습니다.")
    except Exception as e:
        print(f"olefile로 변환 실패: {e}")
    
    # 모든 방법 실패 시 안내 메시지 작성
    error_msg = f"""원본 파일: {hwp_path.name}
변환 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

오류: .hwp 파일을 자동으로 변환할 수 없습니다.

변환 방법:
1. 한글 프로그램으로 파일을 열고 '다른 이름으로 저장' -> '텍스트 파일' 또는 'PDF'로 저장
2. 또는 다음 라이브러리를 설치하여 다시 시도:
   - pyhwp: pip install pyhwp
   - hwp5: pip install hwp5
   - olefile: pip install olefile

참고: Windows 환경에서는 한글 프로그램이 설치되어 있다면 직접 변환하는 것이 가장 정확합니다.
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(error_msg)
    
    print(f"⚠ 변환 실패: {output_path.name} (안내 메시지 저장됨)")
    return False


def convert_xlsx_to_csv_and_json(xlsx_path, output_dir):
    """
    .xlsx 파일을 CSV와 JSON으로 변환합니다.
    여러 시트가 있는 경우 각각 변환합니다.
    """
    print(f"변환 중: {xlsx_path.name}")
    
    try:
        # 엑셀 파일 읽기
        excel_file = pd.ExcelFile(xlsx_path)
        
        for sheet_name in excel_file.sheet_names:
            print(f"  시트 처리 중: {sheet_name}")
            
            # 시트 읽기
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
            
            # 시트 이름을 파일명에 포함 (시트가 여러 개인 경우)
            if len(excel_file.sheet_names) > 1:
                csv_filename = f"{xlsx_path.stem}_{sheet_name}.csv"
                json_filename = f"{xlsx_path.stem}_{sheet_name}.json"
            else:
                csv_filename = f"{xlsx_path.stem}.csv"
                json_filename = f"{xlsx_path.stem}.json"
            
            # CSV로 저장
            csv_path = output_dir / csv_filename
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"  ✓ CSV 저장: {csv_path.name}")
            
            # JSON으로 저장
            json_path = output_dir / json_filename
            # NaN 값을 None으로 변환하여 JSON 호환성 확보
            df_clean = df.where(pd.notnull(df), None)
            data = df_clean.to_dict(orient='records')
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ JSON 저장: {json_path.name}")
        
        print(f"✓ 완료: {xlsx_path.name}")
        return True
        
    except Exception as e:
        print(f"✗ 오류: {xlsx_path.name} 변환 실패 - {e}")
        return False


def main():
    """메인 함수"""
    # 소스 디렉토리
    source_dir = project_root / "docs" / "sources" / "sbiz"
    
    # 출력 디렉토리 (변환된 파일 저장)
    output_dir = project_root / "docs" / "sources" / "sbiz" / "converted"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"소스 디렉토리: {source_dir}")
    print(f"출력 디렉토리: {output_dir}")
    print("-" * 60)
    
    # 파일 변환
    converted_count = 0
    failed_count = 0
    
    for file_path in source_dir.iterdir():
        if file_path.is_file():
            if file_path.suffix.lower() == '.hwp':
                if convert_hwp_to_text(file_path, output_dir):
                    converted_count += 1
                else:
                    failed_count += 1
            elif file_path.suffix.lower() == '.xlsx':
                if convert_xlsx_to_csv_and_json(file_path, output_dir):
                    converted_count += 1
                else:
                    failed_count += 1
            elif file_path.suffix.lower() == '.csv':
                print(f"✓ 건너뜀 (이미 텍스트 포맷): {file_path.name}")
    
    print("-" * 60)
    print(f"변환 완료: {converted_count}개 성공, {failed_count}개 실패")
    print(f"변환된 파일은 {output_dir} 디렉토리에 저장되었습니다.")


if __name__ == "__main__":
    main()
