"""SGIS 연도별 데이터 병합 스크립트

2016~2023년 연도별 데이터를 하나의 파일로 병합합니다.
"""

import sys
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.logger import get_logger

logger = get_logger(__name__)


def find_year_folders(raw_dir: Path) -> List[Path]:
    """연도별 폴더를 찾아서 연도순으로 정렬하여 반환.
    
    Args:
        raw_dir: raw 데이터 디렉토리
        
    Returns:
        연도별 폴더 경로 리스트 (2016~2023 순서)
    """
    folders = []
    for folder in raw_dir.iterdir():
        if folder.is_dir() and folder.name.startswith('sgis_technical_biz_'):
            # 폴더명에서 연도 추출: sgis_technical_biz_{year}_{timestamp}
            parts = folder.name.split('_')
            if len(parts) >= 4:
                try:
                    year = int(parts[3])
                    if 2016 <= year <= 2023:
                        folders.append((year, folder))
                except ValueError:
                    continue
    
    # 연도순으로 정렬
    folders.sort(key=lambda x: x[0])
    return [folder for _, folder in folders]


def merge_json_files(folders: List[Path], output_path: Path, use_wgs84: bool = True) -> None:
    """JSON 파일들을 병합.
    
    Args:
        folders: 연도별 폴더 리스트
        output_path: 출력 파일 경로
        use_wgs84: _wgs84 버전 파일 사용 여부
    """
    all_results = []
    year_counts = {}
    
    for folder in folders:
        # 연도 추출
        year = int(folder.name.split('_')[3])
        
        # 파일명 결정
        if use_wgs84:
            json_file = folder / f"{folder.name}_wgs84.json"
        else:
            # _wgs84가 없는 파일 찾기
            json_files = list(folder.glob("*.json"))
            json_files = [f for f in json_files if "_wgs84" not in f.name]
            if not json_files:
                logger.warning(f"{folder.name}: JSON 파일을 찾을 수 없습니다.")
                continue
            json_file = json_files[0]
        
        if not json_file.exists():
            logger.warning(f"{json_file} 파일이 존재하지 않습니다.")
            continue
        
        logger.info(f"{year}년 데이터 로딩 중: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results = data.get('result', [])
                all_results.extend(results)
                year_counts[year] = len(results)
                logger.info(f"  → {len(results)}개 항목 추가 (총 {len(all_results)}개)")
        except Exception as e:
            logger.error(f"{json_file} 로딩 실패: {e}")
            continue
    
    # 병합된 데이터 구조 생성
    merged_data = {
        "result": all_results,
        "metadata": {
            "merged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "years": sorted(year_counts.keys()),
            "year_counts": year_counts,
            "total_count": len(all_results)
        }
    }
    
    # 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ JSON 병합 완료: {output_path}")
    logger.info(f"   총 {len(all_results)}개 항목 (2016~2023년)")
    for year in sorted(year_counts.keys()):
        logger.info(f"   - {year}년: {year_counts[year]:,}개")


def merge_csv_files(folders: List[Path], output_path: Path, use_wgs84: bool = True) -> None:
    """CSV 파일들을 병합.
    
    Args:
        folders: 연도별 폴더 리스트
        output_path: 출력 파일 경로
        use_wgs84: _wgs84 버전 파일 사용 여부
    """
    all_rows = []
    fieldnames = None
    year_counts = {}
    
    for folder in folders:
        # 연도 추출
        year = int(folder.name.split('_')[3])
        
        # 파일명 결정
        if use_wgs84:
            csv_file = folder / f"{folder.name}_wgs84.csv"
        else:
            # _wgs84가 없는 파일 찾기
            csv_files = list(folder.glob("*.csv"))
            csv_files = [f for f in csv_files if "_wgs84" not in f.name]
            if not csv_files:
                logger.warning(f"{folder.name}: CSV 파일을 찾을 수 없습니다.")
                continue
            csv_file = csv_files[0]
        
        if not csv_file.exists():
            logger.warning(f"{csv_file} 파일이 존재하지 않습니다.")
            continue
        
        logger.info(f"{year}년 데이터 로딩 중: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # 첫 번째 파일에서 필드명 저장
                if fieldnames is None:
                    fieldnames = reader.fieldnames
                
                rows = list(reader)
                all_rows.extend(rows)
                year_counts[year] = len(rows)
                logger.info(f"  → {len(rows)}개 행 추가 (총 {len(all_rows)}개)")
        except Exception as e:
            logger.error(f"{csv_file} 로딩 실패: {e}")
            continue
    
    # 저장
    if fieldnames and all_rows:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        
        logger.info(f"\n✅ CSV 병합 완료: {output_path}")
        logger.info(f"   총 {len(all_rows)}개 행 (2016~2023년)")
        for year in sorted(year_counts.keys()):
            logger.info(f"   - {year}년: {year_counts[year]:,}개")
    else:
        logger.error("병합할 데이터가 없습니다.")


def main():
    """메인 함수"""
    # 경로 설정
    project_root = Path(__file__).parent.parent.parent.parent
    raw_dir = project_root / "data" / "raw" / "sgis"
    output_dir = project_root / "data" / "raw" / "sgis" / "merged"
    
    # 연도별 폴더 찾기
    logger.info("연도별 폴더 검색 중...")
    folders = find_year_folders(raw_dir)
    
    if not folders:
        logger.error("연도별 폴더를 찾을 수 없습니다.")
        return
    
    logger.info(f"발견된 폴더: {len(folders)}개")
    for folder in folders:
        year = folder.name.split('_')[3]
        logger.info(f"  - {year}년: {folder.name}")
    
    # 출력 파일 경로
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_output = output_dir / f"sgis_technical_biz_merged_2016_2023_{timestamp}.json"
    csv_output = output_dir / f"sgis_technical_biz_merged_2016_2023_{timestamp}.csv"
    
    # 병합 실행
    logger.info("\n" + "="*80)
    logger.info("JSON 파일 병합 시작")
    logger.info("="*80)
    merge_json_files(folders, json_output, use_wgs84=True)
    
    logger.info("\n" + "="*80)
    logger.info("CSV 파일 병합 시작")
    logger.info("="*80)
    merge_csv_files(folders, csv_output, use_wgs84=True)
    
    logger.info("\n" + "="*80)
    logger.info("✅ 모든 병합 작업 완료!")
    logger.info(f"   JSON: {json_output}")
    logger.info(f"   CSV: {csv_output}")
    logger.info("="*80)


if __name__ == "__main__":
    main()

