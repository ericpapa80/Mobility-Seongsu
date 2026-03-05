"""수집된 vworld 파일들을 날짜/시간 기반 폴더로 정리하는 스크립트"""

import sys
from pathlib import Path
from datetime import datetime
import shutil
import json

# 프로젝트 루트를 sys.path에 추가
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import get_logger

logger = get_logger(__name__)


def organize_collected_files(base_dir: Path = None):
    """수집된 파일들을 날짜/시간 기반 폴더로 정리
    
    Args:
        base_dir: vworld 데이터 디렉토리 (기본값: data/raw/vworld)
    """
    if base_dir is None:
        base_dir = project_root / "data" / "raw" / "vworld"
    else:
        base_dir = Path(base_dir)
    
    if not base_dir.exists():
        logger.warning(f"디렉토리가 존재하지 않습니다: {base_dir}")
        return
    
    # 파일들을 타임스탬프별로 그룹화
    files_by_timestamp = {}
    
    for file in base_dir.glob("seongsu_*"):
        if not file.is_file():
            continue
        
        # 파일명에서 타임스탬프 추출
        # 예: seongsu_lt-c-spbd_20260127_104517.json -> 20260127_104517
        parts = file.stem.split('_')
        if len(parts) >= 3:
            # 마지막 두 부분이 날짜와 시간
            date_part = parts[-2]
            time_part = parts[-1]
            timestamp = f"{date_part}_{time_part}"
            
            if timestamp not in files_by_timestamp:
                files_by_timestamp[timestamp] = []
            files_by_timestamp[timestamp].append(file)
    
    logger.info(f"발견된 타임스탬프 그룹: {len(files_by_timestamp)}개")
    
    # 각 타임스탬프별로 폴더 생성 및 파일 이동
    for timestamp, files in files_by_timestamp.items():
        folder_name = f"vworld_seongsu_{timestamp}"
        folder_path = base_dir / folder_name
        
        # 폴더가 이미 존재하면 스킵
        if folder_path.exists():
            logger.info(f"폴더가 이미 존재합니다: {folder_path}")
            continue
        
        # 폴더 생성
        folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"폴더 생성: {folder_path}")
        
        # 파일 이동
        for file in files:
            try:
                dest = folder_path / file.name
                shutil.move(str(file), str(dest))
                logger.info(f"  이동: {file.name} -> {folder_path.name}/")
            except Exception as e:
                logger.error(f"  파일 이동 실패 {file.name}: {e}")
    
    logger.info("파일 정리 완료")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="수집된 vworld 파일들을 날짜/시간 기반 폴더로 정리")
    parser.add_argument(
        "--base-dir",
        type=str,
        help="vworld 데이터 디렉토리 (기본값: data/raw/vworld)"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir) if args.base_dir else None
    
    organize_collected_files(base_dir)
