"""여러 번 수집한 vworld 파일들을 summary 기준으로 병합하는 스크립트"""

import sys
from pathlib import Path
from datetime import datetime
import shutil
import json
from collections import defaultdict

# 프로젝트 루트를 sys.path에 추가
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import get_logger

logger = get_logger(__name__)


def merge_collections_by_summary(base_dir: Path = None):
    """summary 파일을 기준으로 같은 수집 세션의 파일들을 병합
    
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
    
    # summary 파일들을 찾아서 수집 세션별로 그룹화
    summary_files = list(base_dir.glob("**/seongsu_collection_summary_*.json"))
    
    if not summary_files:
        logger.info("summary 파일을 찾을 수 없습니다.")
        return
    
    # summary 파일을 읽어서 수집 세션 정보 추출
    sessions = {}
    for summary_file in summary_files:
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # summary의 timestamp를 기준으로 세션 식별
            session_timestamp = summary_data.get('timestamp', '')
            if not session_timestamp:
                continue
            
            # ISO 형식의 timestamp를 폴더명 형식으로 변환
            try:
                dt = datetime.fromisoformat(session_timestamp.replace('Z', '+00:00'))
                session_folder_name = f"vworld_seongsu_{dt.strftime('%Y%m%d_%H%M%S')}"
            except:
                # 파일명에서 추출
                parts = summary_file.stem.split('_')
                if len(parts) >= 3:
                    session_folder_name = f"vworld_seongsu_{parts[-2]}_{parts[-1]}"
                else:
                    continue
            
            if session_folder_name not in sessions:
                sessions[session_folder_name] = {
                    'summary_file': summary_file,
                    'summary_data': summary_data,
                    'files': []
                }
            
        except Exception as e:
            logger.error(f"summary 파일 읽기 실패 {summary_file}: {e}")
            continue
    
    logger.info(f"발견된 수집 세션: {len(sessions)}개")
    
    # 각 세션별로 관련 파일들을 찾아서 병합
    for session_name, session_info in sessions.items():
        summary_file = session_info['summary_file']
        summary_data = session_info['summary_data']
        
        # 세션 폴더 생성
        session_folder = base_dir / session_name
        session_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"세션 폴더: {session_folder}")
        
        # summary 파일 이동
        if summary_file.parent != session_folder:
            dest_summary = session_folder / summary_file.name
            if not dest_summary.exists():
                shutil.move(str(summary_file), str(dest_summary))
                logger.info(f"  이동: {summary_file.name} -> {session_folder.name}/")
        
        # 같은 세션의 다른 파일들 찾기
        # summary의 timestamp와 비슷한 시간대의 파일들을 찾음
        session_dt = datetime.fromisoformat(summary_data['timestamp'].replace('Z', '+00:00'))
        session_time_str = session_dt.strftime('%Y%m%d_%H%M')
        
        # base_dir에서 seongsu_* 파일들 찾기
        for file in base_dir.glob("seongsu_*"):
            if not file.is_file():
                continue
            
            # 파일명에서 타임스탬프 추출
            parts = file.stem.split('_')
            if len(parts) >= 3:
                file_date = parts[-2]
                file_time = parts[-1][:4]  # HHMM만 추출
                file_time_str = f"{file_date}_{file_time}"
                
                # 같은 시간대(분 단위)의 파일이면 같은 세션으로 간주
                if file_time_str == session_time_str:
                    dest = session_folder / file.name
                    if not dest.exists():
                        try:
                            shutil.move(str(file), str(dest))
                            logger.info(f"  이동: {file.name} -> {session_folder.name}/")
                        except Exception as e:
                            logger.error(f"  파일 이동 실패 {file.name}: {e}")
        
        # 하위 폴더에 있는 같은 세션의 파일들도 확인
        for subfolder in base_dir.glob("vworld_seongsu_*"):
            if not subfolder.is_dir():
                continue
            
            # 같은 세션이면 파일들을 병합
            if subfolder.name == session_name:
                continue  # 이미 처리한 폴더
            
            # 하위 폴더의 파일들을 확인하여 같은 시간대면 병합
            for file in subfolder.glob("seongsu_*"):
                if not file.is_file():
                    continue
                
                parts = file.stem.split('_')
                if len(parts) >= 3:
                    file_date = parts[-2]
                    file_time = parts[-1][:4]
                    file_time_str = f"{file_date}_{file_time}"
                    
                    if file_time_str == session_time_str:
                        dest = session_folder / file.name
                        if not dest.exists():
                            try:
                                shutil.move(str(file), str(dest))
                                logger.info(f"  병합: {file.name} -> {session_folder.name}/")
                            except Exception as e:
                                logger.error(f"  파일 이동 실패 {file.name}: {e}")
            
            # 하위 폴더가 비어있으면 삭제
            try:
                if not any(subfolder.iterdir()):
                    subfolder.rmdir()
                    logger.info(f"  빈 폴더 삭제: {subfolder.name}")
            except:
                pass
    
    logger.info("파일 병합 완료")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="여러 번 수집한 vworld 파일들을 summary 기준으로 병합")
    parser.add_argument(
        "--base-dir",
        type=str,
        help="vworld 데이터 디렉토리 (기본값: data/raw/vworld)"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir) if args.base_dir else None
    
    merge_collections_by_summary(base_dir)
