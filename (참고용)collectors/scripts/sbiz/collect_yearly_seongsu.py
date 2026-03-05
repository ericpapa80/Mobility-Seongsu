"""연도별 성수동 상가업소 수집.

각 연도별 CSV 파일에서 성수동 상가업소만 추출하여 연도별로 별도 파일로 저장합니다.
"""

import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger
from core.file_handler import FileHandler

logger = get_logger(__name__)


def extract_seongsu_from_csv(csv_file: Path, year: int) -> pd.DataFrame:
    """CSV 파일에서 성수동 상가업소만 추출.
    
    Args:
        csv_file: CSV 파일 경로
        year: 연도
        
    Returns:
        성수동 상가업소 DataFrame
    """
    logger.info(f"\n[{year}년] CSV 파일 로딩 중: {csv_file.name}")
    
    if not csv_file.exists():
        logger.warning(f"  파일이 존재하지 않습니다: {csv_file}")
        return pd.DataFrame()
    
    try:
        # 성수동 행정동명
        seongsu_dongs = ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']
        
        # CSV 파일 읽기 (큰 파일이므로 청크 단위로 읽기)
        chunks = []
        chunk_size = 10000
        
        logger.info(f"  파일 읽기 중...")
        for chunk in pd.read_csv(csv_file, encoding='utf-8-sig', chunksize=chunk_size, low_memory=False):
            # 행정동명 컬럼 찾기
            dong_col = None
            for col in chunk.columns:
                if '행정동명' in col or 'adongNm' in col:
                    dong_col = col
                    break
            
            if dong_col:
                # 성수동 필터링
                chunk = chunk[chunk[dong_col].isin(seongsu_dongs)]
                if len(chunk) > 0:
                    chunks.append(chunk)
            else:
                logger.warning(f"  행정동명 컬럼을 찾을 수 없습니다. 컬럼: {list(chunk.columns)[:10]}")
        
        if chunks:
            df = pd.concat(chunks, ignore_index=True)
            logger.info(f"  성수동 업소 수: {len(df):,}개")
            
            # 행정동별 통계
            if dong_col:
                logger.info(f"  행정동별 업소 수:")
                for dong in seongsu_dongs:
                    count = len(df[df[dong_col] == dong])
                    if count > 0:
                        logger.info(f"    {dong}: {count:,}개")
            
            return df
        else:
            logger.warning(f"  성수동 업소가 없습니다.")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"  CSV 파일 로딩 실패: {e}")
        return pd.DataFrame()


def save_yearly_data(df: pd.DataFrame, year: int, output_dir: Path):
    """연도별 데이터를 JSON과 CSV로 저장.
    
    Args:
        df: DataFrame
        year: 연도
        output_dir: 출력 디렉토리
    """
    if df.empty:
        logger.warning(f"  [{year}년] 저장할 데이터가 없습니다.")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_handler = FileHandler()
    
    # JSON 저장
    json_path = output_dir / f"sbiz_stores_seongsu_{year}.json"
    data = {
        'metadata': {
            'year': year,
            'collected_at': datetime.now().isoformat(),
            'total_count': len(df),
            'source': 'filedata'
        },
        'stores': df.to_dict('records')
    }
    file_handler.save_json(data, json_path)
    logger.info(f"  JSON 저장: {json_path}")
    
    # CSV 저장
    csv_path = output_dir / f"sbiz_stores_seongsu_{year}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"  CSV 저장: {csv_path}")


def main():
    """연도별 성수동 상가업소 수집 메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='연도별 성수동 상가업소 수집')
    parser.add_argument('--csv-dir', type=str,
                       default='data/raw/sbiz/filedata',
                       help='CSV 파일 디렉토리')
    parser.add_argument('--output-dir', type=str,
                       default='data/raw/sbiz/yearly_seongsu',
                       help='출력 디렉토리')
    parser.add_argument('--years', type=str,
                       default='2017,2018,2019,2020,2021,2022,2023,2024,2025',
                       help='수집할 연도 리스트 (쉼표로 구분)')
    
    args = parser.parse_args()
    
    # 연도 파싱
    years = [int(y.strip()) for y in args.years.split(',')]
    logger.info(f"수집할 연도: {years}")
    
    # CSV 파일 디렉토리
    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)
    
    # 연도별 CSV 파일 찾기
    csv_files = {}
    for year in years:
        # 파일명 패턴: 소상공인시장진흥공단_상가(상권)정보_서울_YYYYMM.csv
        # 또는 YYYY12.csv (12월 데이터)
        patterns = [
            f"*_{year}*.csv",
            f"*{year}12.csv",
            f"*{year}10.csv"
        ]
        
        found = False
        for pattern in patterns:
            files = list(csv_dir.glob(pattern))
            if files:
                # 가장 최근 파일 선택 (같은 연도에 여러 파일이 있을 수 있음)
                csv_files[year] = sorted(files, reverse=True)[0]
                logger.info(f"  {year}년: {csv_files[year].name}")
                found = True
                break
        
        if not found:
            logger.warning(f"  {year}년: 파일을 찾을 수 없습니다")
    
    if not csv_files:
        logger.error("수집할 CSV 파일이 없습니다.")
        return
    
    logger.info(f"\n{'='*60}")
    logger.info("연도별 성수동 상가업소 수집 시작")
    logger.info(f"{'='*60}")
    
    # 연도별로 성수동 추출 및 저장
    total_stores = 0
    for year in sorted(years):
        if year not in csv_files:
            continue
        
        csv_file = csv_files[year]
        df = extract_seongsu_from_csv(csv_file, year)
        
        if not df.empty:
            save_yearly_data(df, year, output_dir)
            total_stores += len(df)
    
    logger.info(f"\n{'='*60}")
    logger.info("연도별 성수동 상가업소 수집 완료!")
    logger.info(f"{'='*60}")
    logger.info(f"총 수집된 업소 수: {total_stores:,}개 (중복 포함)")
    logger.info(f"저장 위치: {output_dir}")


if __name__ == "__main__":
    main()

