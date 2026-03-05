"""
CSV 파일의 인코딩을 UTF-8로 변환하는 스크립트
"""

import sys
from pathlib import Path
import chardet

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def detect_encoding(file_path):
    """파일의 인코딩을 감지합니다."""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)  # 처음 10KB만 읽어서 감지
        result = chardet.detect(raw_data)
        return result['encoding'], result['confidence']


def convert_csv_to_utf8(input_path, output_path=None, source_encoding=None):
    """
    CSV 파일을 UTF-8로 변환합니다.
    
    Args:
        input_path: 입력 파일 경로
        output_path: 출력 파일 경로 (None이면 원본 파일 덮어쓰기)
        source_encoding: 원본 인코딩 (None이면 자동 감지)
    """
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path
    else:
        output_path = Path(output_path)
    
    # 인코딩 감지
    if source_encoding is None:
        detected_encoding, confidence = detect_encoding(input_path)
        print(f"감지된 인코딩: {detected_encoding} (신뢰도: {confidence:.2%})")
        source_encoding = detected_encoding
    
    # 파일 읽기
    try:
        with open(input_path, 'r', encoding=source_encoding) as f:
            content = f.read()
    except UnicodeDecodeError as e:
        print(f"인코딩 오류: {e}")
        print("다른 인코딩을 시도합니다...")
        # 일반적인 한국어 인코딩들 시도
        for enc in ['cp949', 'euc-kr', 'utf-8', 'latin1']:
            try:
                with open(input_path, 'r', encoding=enc) as f:
                    content = f.read()
                print(f"성공: {enc} 인코딩으로 읽었습니다.")
                source_encoding = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            raise Exception("파일을 읽을 수 없습니다. 인코딩을 확인해주세요.")
    
    # UTF-8로 저장 (BOM 없이)
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write(content)
    
    print(f"✓ 변환 완료: {input_path.name} -> {output_path.name} (UTF-8)")
    return True


def main():
    """메인 함수"""
    csv_file = project_root / "docs" / "sources" / "sbiz" / "소상공인시장진흥공단_주요상권현황_20240101.csv"
    
    if not csv_file.exists():
        print(f"파일을 찾을 수 없습니다: {csv_file}")
        return
    
    print(f"파일 변환 중: {csv_file.name}")
    print("-" * 60)
    
    convert_csv_to_utf8(csv_file)
    
    print("-" * 60)
    print("변환 완료!")


if __name__ == "__main__":
    main()
