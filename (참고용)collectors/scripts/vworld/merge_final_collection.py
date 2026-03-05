"""최종 수집 결과를 하나의 폴더로 병합하는 스크립트"""

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


def merge_final_collection(base_dir: Path = None):
    """최신 수집 결과를 기준으로 모든 관련 파일을 하나의 폴더로 병합
    
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
    
    # 모든 summary 파일 찾기
    summary_files = list(base_dir.glob("**/seongsu_collection_summary_*.json"))
    
    if not summary_files:
        logger.info("summary 파일을 찾을 수 없습니다.")
        return
    
    # 가장 최신 summary 파일 찾기
    latest_summary = None
    latest_time = None
    
    for summary_file in summary_files:
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            timestamp_str = summary_data.get('timestamp', '')
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if latest_time is None or dt > latest_time:
                        latest_time = dt
                        latest_summary = (summary_file, summary_data)
                except:
                    pass
        except Exception as e:
            logger.error(f"summary 파일 읽기 실패 {summary_file}: {e}")
    
    if not latest_summary:
        logger.warning("유효한 summary 파일을 찾을 수 없습니다.")
        return
    
    summary_file, summary_data = latest_summary
    logger.info(f"최신 수집 세션: {summary_data.get('timestamp', 'N/A')}")
    
    # 최종 폴더명 생성 (summary의 timestamp 기준)
    final_folder_name = f"vworld_seongsu_{latest_time.strftime('%Y%m%d_%H%M%S')}"
    final_folder = base_dir / final_folder_name
    final_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"최종 폴더: {final_folder}")
    
    # summary 파일 이동
    dest_summary = final_folder / summary_file.name
    if summary_file != dest_summary:
        if dest_summary.exists():
            dest_summary.unlink()
        shutil.move(str(summary_file), str(dest_summary))
        logger.info(f"  이동: {summary_file.name}")
    
    # 모든 seongsu_* 파일들을 최종 폴더로 이동
    moved_files = set()
    
    # base_dir의 직접 파일들
    for file in base_dir.glob("seongsu_*"):
        if not file.is_file():
            continue
        
        dest = final_folder / file.name
        if not dest.exists():
            try:
                shutil.move(str(file), str(dest))
                moved_files.add(file.name)
                logger.info(f"  이동: {file.name}")
            except Exception as e:
                logger.error(f"  파일 이동 실패 {file.name}: {e}")
    
    # 하위 폴더의 파일들도 병합
    for subfolder in base_dir.glob("vworld_seongsu_*"):
        if not subfolder.is_dir() or subfolder == final_folder:
            continue
        
        for file in subfolder.glob("seongsu_*"):
            if not file.is_file():
                continue
            
            dest = final_folder / file.name
            if not dest.exists():
                try:
                    shutil.move(str(file), str(dest))
                    moved_files.add(file.name)
                    logger.info(f"  병합: {file.name} (from {subfolder.name})")
                except Exception as e:
                    logger.error(f"  파일 이동 실패 {file.name}: {e}")
        
        # 하위 폴더가 비어있으면 삭제
        try:
            if not any(subfolder.iterdir()):
                subfolder.rmdir()
                logger.info(f"  빈 폴더 삭제: {subfolder.name}")
        except:
            pass
    
    logger.info(f"병합 완료: 총 {len(moved_files)}개 파일")
    logger.info(f"최종 폴더: {final_folder}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="최종 수집 결과를 하나의 폴더로 병합")
    parser.add_argument(
        "--base-dir",
        type=str,
        help="vworld 데이터 디렉토리 (기본값: data/raw/vworld)"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir) if args.base_dir else None
    
    merge_final_collection(base_dir)
