"""기존 CSV 파일에 JSON의 좌표 정보를 추가하는 스크립트"""

import sys
from pathlib import Path
import json
import pandas as pd

# 프로젝트 루트를 sys.path에 추가
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import get_logger
from scripts.vworld.collect_seongsu import extract_coordinates_from_geometry, epsg3857_to_wgs84

logger = get_logger(__name__)


def add_coordinates_to_csv(json_file: Path, csv_file: Path = None):
    """JSON 파일의 좌표 정보를 CSV에 추가
    
    Args:
        json_file: JSON 파일 경로
        csv_file: CSV 파일 경로 (None이면 자동으로 찾음)
    """
    if not json_file.exists():
        logger.error(f"JSON 파일을 찾을 수 없습니다: {json_file}")
        return
    
    # CSV 파일 경로 결정
    if csv_file is None:
        csv_file = json_file.with_suffix('.csv')
    
    if not csv_file.exists():
        logger.error(f"CSV 파일을 찾을 수 없습니다: {csv_file}")
        return
    
    logger.info(f"처리 중: {json_file.name} -> {csv_file.name}")
    
    # JSON 파일 읽기
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        logger.error(f"JSON 파일 읽기 실패: {e}")
        return
    
    # CSV 파일 읽기
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
    except Exception as e:
        logger.error(f"CSV 파일 읽기 실패: {e}")
        return
    
    # features에서 좌표 정보 추출
    features = json_data.get('features', [])
    
    if len(features) != len(df):
        logger.warning(f"피처 수 불일치: JSON={len(features)}, CSV={len(df)}")
    
    # 좌표 정보 컬럼 초기화
    coord_columns = [
        'geometry_type', 'x', 'y', 'lon', 'lat',
        'centroid_x', 'centroid_y', 'centroid_lon', 'centroid_lat', 'wkt'
    ]
    
    for col in coord_columns:
        if col not in df.columns:
            df[col] = None
    
    # 각 피처의 좌표 정보 추출하여 CSV에 추가
    for idx, feature in enumerate(features):
        if idx >= len(df):
            break
        
        if 'geometry' in feature:
            geometry = feature['geometry']
            coords_info = extract_coordinates_from_geometry(geometry, crs="EPSG:3857")
            
            # CSV 행에 좌표 정보 추가
            for col in coord_columns:
                df.at[idx, col] = coords_info.get(col)
    
    # CSV 저장
    try:
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        logger.info(f"  ✓ 좌표 정보 추가 완료: {csv_file}")
    except Exception as e:
        logger.error(f"  ✗ CSV 저장 실패: {e}")


def process_folder(folder_path: Path):
    """폴더 내의 모든 JSON/CSV 쌍 처리
    
    Args:
        folder_path: 처리할 폴더 경로
    """
    if not folder_path.exists() or not folder_path.is_dir():
        logger.error(f"폴더를 찾을 수 없습니다: {folder_path}")
        return
    
    # JSON 파일 찾기
    json_files = list(folder_path.glob("seongsu_*.json"))
    json_files = [f for f in json_files if 'summary' not in f.name]
    
    logger.info(f"발견된 JSON 파일: {len(json_files)}개")
    
    for json_file in json_files:
        csv_file = json_file.with_suffix('.csv')
        if csv_file.exists():
            add_coordinates_to_csv(json_file, csv_file)
        else:
            logger.warning(f"  CSV 파일 없음: {csv_file.name}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="기존 CSV 파일에 JSON의 좌표 정보 추가")
    parser.add_argument(
        "--folder",
        type=str,
        help="처리할 폴더 경로 (기본값: 최신 vworld_seongsu 폴더)"
    )
    parser.add_argument(
        "--json",
        type=str,
        help="JSON 파일 경로"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="CSV 파일 경로"
    )
    
    args = parser.parse_args()
    
    if args.json:
        json_file = Path(args.json)
        csv_file = Path(args.csv) if args.csv else None
        add_coordinates_to_csv(json_file, csv_file)
    elif args.folder:
        folder_path = Path(args.folder)
        process_folder(folder_path)
    else:
        # 기본값: 최신 vworld_seongsu 폴더
        base_dir = project_root / "data" / "raw" / "vworld"
        folders = sorted(base_dir.glob("vworld_seongsu_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if folders:
            logger.info(f"최신 폴더 처리: {folders[0].name}")
            process_folder(folders[0])
        else:
            logger.warning("처리할 폴더를 찾을 수 없습니다.")
