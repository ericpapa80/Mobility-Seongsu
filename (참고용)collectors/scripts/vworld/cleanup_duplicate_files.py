"""중복된 수집 파일들을 정리하고 최신 파일만 유지하는 스크립트"""

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


def cleanup_duplicate_files(base_dir: Path = None, keep_latest_only: bool = True):
    """중복된 수집 파일들을 정리
    
    Args:
        base_dir: vworld 데이터 디렉토리 (기본값: data/raw/vworld)
        keep_latest_only: 최신 파일만 유지할지 여부
    """
    if base_dir is None:
        base_dir = project_root / "data" / "raw" / "vworld"
    else:
        base_dir = Path(base_dir)
    
    if not base_dir.exists():
        logger.warning(f"디렉토리가 존재하지 않습니다: {base_dir}")
        return
    
    # 각 폴더별로 처리
    for folder in base_dir.glob("vworld_seongsu_*"):
        if not folder.is_dir():
            continue
        
        logger.info(f"처리 중: {folder.name}")
        
        # 레이어별로 파일 그룹화
        files_by_layer = {}
        
        for file in folder.glob("seongsu_*"):
            if not file.is_file():
                continue
            
            # summary 파일은 제외
            if 'summary' in file.name:
                continue
            
            # 레이어명 추출
            # 예: seongsu_lt-c-spbd_20260127_104517.json -> lt-c-spbd
            parts = file.stem.split('_')
            if len(parts) >= 3:
                # seongsu 제외하고 레이어명 추출
                layer_name = '_'.join(parts[1:-2])  # lt-c-spbd 또는 lt-c-landinfobasemap
                file_type = file.suffix[1:]  # json 또는 csv
                
                key = f"{layer_name}_{file_type}"
                
                if key not in files_by_layer:
                    files_by_layer[key] = []
                
                # 파일의 수정 시간과 함께 저장
                files_by_layer[key].append({
                    'file': file,
                    'mtime': file.stat().st_mtime,
                    'timestamp': '_'.join(parts[-2:])  # 날짜_시간
                })
        
        # 각 레이어별로 최신 파일만 유지
        for layer_key, files in files_by_layer.items():
            if len(files) <= 1:
                continue
            
            # 타임스탬프 기준으로 정렬 (최신이 마지막)
            files.sort(key=lambda x: x['timestamp'])
            
            # 최신 파일
            latest = files[-1]
            old_files = files[:-1]
            
            logger.info(f"  레이어: {layer_key}")
            logger.info(f"    최신: {latest['file'].name} ({latest['timestamp']})")
            
            # 오래된 파일들 삭제
            for old_file_info in old_files:
                try:
                    old_file_info['file'].unlink()
                    logger.info(f"    삭제: {old_file_info['file'].name} ({old_file_info['timestamp']})")
                except Exception as e:
                    logger.error(f"    파일 삭제 실패 {old_file_info['file'].name}: {e}")
        
        # summary 파일도 최신 것만 유지
        summary_files = list(folder.glob("seongsu_collection_summary_*.json"))
        if len(summary_files) > 1:
            summary_files.sort(key=lambda f: f.stat().st_mtime)
            latest_summary = summary_files[-1]
            old_summaries = summary_files[:-1]
            
            logger.info(f"  Summary 파일:")
            logger.info(f"    최신: {latest_summary.name}")
            
            for old_summary in old_summaries:
                try:
                    old_summary.unlink()
                    logger.info(f"    삭제: {old_summary.name}")
                except Exception as e:
                    logger.error(f"    파일 삭제 실패 {old_summary.name}: {e}")
    
    logger.info("중복 파일 정리 완료")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="중복된 수집 파일들을 정리하고 최신 파일만 유지")
    parser.add_argument(
        "--base-dir",
        type=str,
        help="vworld 데이터 디렉토리 (기본값: data/raw/vworld)"
    )
    parser.add_argument(
        "--keep-all",
        action="store_true",
        help="모든 파일 유지 (기본값: 최신만 유지)"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir) if args.base_dir else None
    
    cleanup_duplicate_files(base_dir, keep_latest_only=not args.keep_all)
