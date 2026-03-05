"""
CSV 파일의 center 컬럼을 x, y 컬럼으로 분리하는 스크립트
"""

import sys
import pandas as pd
import ast
from pathlib import Path
import json

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def parse_center_coordinates(center_str):
    """
    center 컬럼의 문자열을 파싱하여 [lng, lat] 리스트로 변환
    
    Args:
        center_str: "[127.0536821, 37.5355361]" 형식의 문자열
    
    Returns:
        (x, y) 튜플 또는 (None, None)
    """
    if pd.isna(center_str) or not center_str:
        return None, None
    
    try:
        # 문자열을 리스트로 파싱
        if isinstance(center_str, str):
            # JSON 형식으로 파싱 시도
            try:
                coords = json.loads(center_str)
            except json.JSONDecodeError:
                # ast.literal_eval로 파싱 시도
                try:
                    coords = ast.literal_eval(center_str)
                except (ValueError, SyntaxError):
                    return None, None
        else:
            coords = center_str
        
        if isinstance(coords, list) and len(coords) >= 2:
            x = float(coords[0])  # 경도 (lng)
            y = float(coords[1])  # 위도 (lat)
            return x, y
        else:
            return None, None
    except (ValueError, TypeError, IndexError) as e:
        print(f"Warning: Failed to parse center: {center_str}, Error: {e}")
        return None, None


def add_xy_columns_to_csv(csv_path, output_path=None):
    """
    CSV 파일의 center 컬럼을 x, y 컬럼으로 분리
    
    Args:
        csv_path: 입력 CSV 파일 경로
        output_path: 출력 CSV 파일 경로 (None이면 원본 파일 덮어쓰기)
    """
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        print(f"Error: 파일을 찾을 수 없습니다: {csv_path}")
        return False
    
    if output_path is None:
        output_path = csv_path
    else:
        output_path = Path(output_path)
    
    print(f"처리 중: {csv_path.name}")
    
    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        print(f"  총 행 수: {len(df)}")
        print(f"  컬럼: {list(df.columns)}")
        
        # center 컬럼 확인
        if 'center' not in df.columns:
            print(f"  Warning: 'center' 컬럼이 없습니다. 건너뜁니다.")
            return False
        
        # center 컬럼을 x, y로 분리
        print(f"  center 컬럼을 x, y로 분리 중...")
        coordinates = df['center'].apply(parse_center_coordinates)
        df['x'] = coordinates.apply(lambda x: x[0] if x[0] is not None else None)
        df['y'] = coordinates.apply(lambda x: x[1] if x[1] is not None else None)
        
        # x, y 컬럼을 center 컬럼 바로 다음에 배치
        cols = list(df.columns)
        cols.remove('x')
        cols.remove('y')
        
        # center 컬럼의 인덱스 찾기
        center_idx = cols.index('center')
        # center 다음에 x, y 삽입
        cols.insert(center_idx + 1, 'x')
        cols.insert(center_idx + 2, 'y')
        
        df = df[cols]
        
        # 통계 출력
        x_valid = df['x'].notna().sum()
        y_valid = df['y'].notna().sum()
        print(f"  ✓ 완료: x 컬럼 {x_valid}개, y 컬럼 {y_valid}개 값 생성")
        
        # CSV 파일 저장
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"  ✓ 저장 완료: {output_path.name}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    # 처리할 CSV 파일들
    base_dir = project_root / "data" / "raw" / "openup" / "20251210_105005"
    
    csv_files = [
        base_dir / "openup_seongsu_buildings_20251210_105005.csv",
        # stores 파일에는 center 컬럼이 없으므로 제외
        # base_dir / "openup_seongsu_stores_20251210_105005.csv",
    ]
    
    print("=" * 80)
    print("CSV 파일 center 컬럼을 x, y 컬럼으로 분리")
    print("=" * 80)
    print()
    
    success_count = 0
    for csv_file in csv_files:
        if csv_file.exists():
            if add_xy_columns_to_csv(csv_file):
                success_count += 1
            print()
        else:
            print(f"파일을 찾을 수 없습니다: {csv_file}")
            print()
    
    print("=" * 80)
    print(f"처리 완료: {success_count}/{len(csv_files)}개 파일 성공")
    print("=" * 80)


if __name__ == "__main__":
    main()
