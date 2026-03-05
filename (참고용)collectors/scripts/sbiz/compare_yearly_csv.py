"""CSV 파일 비교를 통한 연도별 개폐업 추적.

보유한 연도별 CSV 파일들을 비교하여 각 업소의 연도별 존재 여부를 확인하고,
개업/폐업/변경없음 정보를 추가합니다.
"""

import sys
from pathlib import Path
from typing import Dict, Set, List
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger

logger = get_logger(__name__)


def load_yearly_stores(csv_files: Dict[int, Path], seongsu_dongs: List[str] = None) -> Dict[int, Set[str]]:
    """연도별 CSV 파일에서 성수동 업소 ID 추출.
    
    Args:
        csv_files: {year: csv_file_path} 형태의 딕셔너리
        seongsu_dongs: 성수동 행정동명 리스트 (필터링용)
        
    Returns:
        {year: {bizesId}} 형태의 딕셔너리
    """
    yearly_stores = {}
    
    for year, csv_file in sorted(csv_files.items()):
        logger.info(f"\n[{year}년] CSV 파일 로딩 중: {csv_file.name}")
        
        if not csv_file.exists():
            logger.warning(f"  파일이 존재하지 않습니다: {csv_file}")
            yearly_stores[year] = set()
            continue
        
        try:
            # CSV 파일 읽기 (큰 파일이므로 청크 단위로 읽기)
            chunks = []
            chunk_size = 10000
            
            for chunk in pd.read_csv(csv_file, encoding='utf-8-sig', chunksize=chunk_size, low_memory=False):
                # 성수동 필터링
                if seongsu_dongs:
                    # 행정동명 컬럼 확인
                    dong_col = None
                    for col in chunk.columns:
                        if '행정동명' in col or 'adongNm' in col:
                            dong_col = col
                            break
                    
                    if dong_col:
                        chunk = chunk[chunk[dong_col].isin(seongsu_dongs)]
                
                chunks.append(chunk)
            
            if chunks:
                df = pd.concat(chunks, ignore_index=True)
            else:
                df = pd.DataFrame()
            
            # 상가업소번호 컬럼 찾기
            bizes_id_col = None
            for col in df.columns:
                if '상가업소번호' in col or 'bizesId' in col:
                    bizes_id_col = col
                    break
            
            if bizes_id_col is None:
                logger.warning(f"  상가업소번호 컬럼을 찾을 수 없습니다. 컬럼: {list(df.columns)[:5]}")
                yearly_stores[year] = set()
                continue
            
            # 업소 ID 추출
            bizes_ids = set(df[bizes_id_col].dropna().astype(str).unique())
            yearly_stores[year] = bizes_ids
            logger.info(f"  성수동 업소 수: {len(bizes_ids):,}개")
            
        except Exception as e:
            logger.error(f"  CSV 파일 로딩 실패: {e}")
            yearly_stores[year] = set()
    
    return yearly_stores


def compare_yearly_stores(yearly_stores: Dict[int, Set[str]]) -> Dict[str, Dict]:
    """연도별 업소 존재 여부 비교하여 개폐업 추적.
    
    Args:
        yearly_stores: {year: {bizesId}} 형태의 딕셔너리
        
    Returns:
        {bizesId: {openYear, closeYear, yearStatus}} 형태의 딕셔너리
    """
    store_status = {}
    years = sorted(yearly_stores.keys())
    
    # 모든 연도의 업소 ID 수집
    all_bizes_ids = set()
    for year in years:
        all_bizes_ids.update(yearly_stores[year])
    
    logger.info(f"\n{'='*60}")
    logger.info("연도별 비교 분석 중...")
    logger.info(f"{'='*60}")
    logger.info(f"전체 추적 업소 수: {len(all_bizes_ids):,}개")
    logger.info(f"비교 연도: {years}")
    
    # 각 업소별로 연도별 상태 추적
    for bizes_id in all_bizes_ids:
        year_status = {}  # {year: 'exist' or None}
        first_seen_year = None
        last_seen_year = None
        
        # 각 연도별 존재 여부 확인
        for year in years:
            exists = bizes_id in yearly_stores[year]
            year_status[year] = 'exist' if exists else None
            
            if exists:
                if first_seen_year is None:
                    first_seen_year = year
                last_seen_year = year
        
        # 개업/폐업 연도 판단
        open_year = first_seen_year
        close_year = None
        
        # 가장 최근 연도에 없으면 폐업으로 판단
        if years and last_seen_year and last_seen_year < max(years):
            # 마지막으로 본 연도 이후에 없으면 폐업
            close_year = last_seen_year
        
        # 연도별 상태 문자열 생성 (예: "2022,2023,2024")
        existing_years = [str(year) for year in years if year_status.get(year) == 'exist']
        year_status_str = ','.join(existing_years) if existing_years else ''
        
        store_status[bizes_id] = {
            'openYear': open_year,
            'closeYear': close_year,
            'yearStatus': year_status,
            'existingYears': year_status_str,
            'firstSeenYear': first_seen_year,
            'lastSeenYear': last_seen_year
        }
    
    # 통계
    opened = sum(1 for s in store_status.values() if s.get('openYear'))
    closed = sum(1 for s in store_status.values() if s.get('closeYear'))
    operating = sum(1 for s in store_status.values() 
                   if s.get('openYear') and not s.get('closeYear'))
    
    logger.info(f"\n분석 결과:")
    logger.info(f"  개업 추적: {opened:,}개")
    logger.info(f"  폐업 추적: {closed:,}개")
    logger.info(f"  현재 영업중: {operating:,}개")
    
    return store_status


def add_yearly_columns_to_csv(
    base_csv_path: Path,
    store_status: Dict[str, Dict],
    output_csv_path: Path,
    years: List[int]
):
    """CSV 파일에 연도별 컬럼 추가.
    
    Args:
        base_csv_path: 기본 CSV 파일 경로
        store_status: 업소별 상태 정보
        output_csv_path: 출력 CSV 파일 경로
        years: 연도 리스트
    """
    logger.info(f"\n{'='*60}")
    logger.info("CSV 파일에 연도별 컬럼 추가 중...")
    logger.info(f"{'='*60}")
    
    # CSV 파일 읽기
    logger.info(f"기본 CSV 파일 로딩: {base_csv_path}")
    
    # 상가업소번호 컬럼 찾기
    df = pd.read_csv(base_csv_path, encoding='utf-8-sig', low_memory=False, nrows=1)
    bizes_id_col = None
    for col in df.columns:
        if '상가업소번호' in col or 'bizesId' in col:
            bizes_id_col = col
            break
    
    if bizes_id_col is None:
        logger.error(f"상가업소번호 컬럼을 찾을 수 없습니다. 컬럼: {list(df.columns)[:10]}")
        return
    
    # 전체 데이터 읽기
    logger.info("전체 데이터 로딩 중...")
    df = pd.read_csv(base_csv_path, encoding='utf-8-sig', low_memory=False)
    logger.info(f"  총 {len(df):,}개 행")
    
    # 연도별 컬럼 추가
    for year in sorted(years):
        col_name = f'{year}년_존재'
        df[col_name] = df[bizes_id_col].astype(str).apply(
            lambda x: 'O' if store_status.get(x, {}).get('yearStatus', {}).get(year) == 'exist' else ''
        )
        logger.info(f"  {col_name} 컬럼 추가 완료")
    
    # 개업/폐업/변경없음 컬럼 추가
    def get_status_info(bizes_id_str):
        status = store_status.get(bizes_id_str, {})
        open_year = status.get('openYear')
        close_year = status.get('closeYear')
        existing_years = status.get('existingYears', '')
        
        # 개업 연도
        open_str = str(open_year) if open_year else ''
        
        # 폐업 연도
        close_str = str(close_year) if close_year else ''
        
        # 변경없음: 모든 연도에 존재하는 경우
        if bizes_id_str in store_status and existing_years:
            existing_years_list = existing_years.split(',')
            all_years_exist = len(existing_years_list) == len(years)
            change_none = 'O' if all_years_exist else ''
        else:
            change_none = ''
        
        return pd.Series({
            '개업연도': open_str,
            '폐업연도': close_str,
            '변경없음': change_none,
            '존재연도': existing_years
        })
    
    logger.info("개업/폐업/변경없음 컬럼 추가 중...")
    status_df = df[bizes_id_col].astype(str).apply(get_status_info)
    df = pd.concat([df, status_df], axis=1)
    
    # 저장
    logger.info(f"결과 저장 중: {output_csv_path}")
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"  저장 완료: {len(df):,}개 행, {len(df.columns)}개 컬럼")
    
    # 통계
    logger.info(f"\n컬럼 추가 통계:")
    logger.info(f"  개업연도 기입: {df['개업연도'].notna().sum():,}개")
    logger.info(f"  폐업연도 기입: {df['폐업연도'].notna().sum():,}개")
    logger.info(f"  변경없음: {df['변경없음'].notna().sum():,}개")


def main():
    """CSV 파일 비교 메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='CSV 파일 비교를 통한 연도별 개폐업 추적')
    parser.add_argument('--csv-dir', type=str,
                       default='data/raw/sbiz/filedata',
                       help='CSV 파일 디렉토리')
    parser.add_argument('--base-csv', type=str,
                       help='기본 CSV 파일 경로 (결과를 추가할 파일)')
    parser.add_argument('--output-csv', type=str,
                       help='출력 CSV 파일 경로')
    parser.add_argument('--years', type=str,
                       default='2022,2023,2024,2025',
                       help='비교할 연도 리스트 (쉼표로 구분)')
    
    args = parser.parse_args()
    
    # 연도 파싱
    years = [int(y.strip()) for y in args.years.split(',')]
    logger.info(f"비교할 연도: {years}")
    
    # CSV 파일 찾기
    csv_dir = Path(args.csv_dir)
    csv_files = {}
    
    for year in years:
        # 파일명 패턴: 소상공인시장진흥공단_상가(상권)정보_서울_YYYYMM.csv
        pattern = f"*_{year}*.csv"
        files = list(csv_dir.glob(pattern))
        if files:
            csv_files[year] = files[0]
            logger.info(f"  {year}년: {files[0].name}")
        else:
            logger.warning(f"  {year}년: 파일을 찾을 수 없습니다")
    
    if not csv_files:
        logger.error("비교할 CSV 파일이 없습니다.")
        return
    
    # 성수동 행정동명
    seongsu_dongs = ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']
    
    # 연도별 업소 ID 추출
    yearly_stores = load_yearly_stores(csv_files, seongsu_dongs=seongsu_dongs)
    
    # 연도별 비교 분석
    store_status = compare_yearly_stores(yearly_stores)
    
    # 기본 CSV 파일에 컬럼 추가
    if args.base_csv:
        base_csv_path = Path(args.base_csv)
        if args.output_csv:
            output_csv_path = Path(args.output_csv)
        else:
            output_csv_path = base_csv_path.parent / f"{base_csv_path.stem}_with_yearly{base_csv_path.suffix}"
        
        add_yearly_columns_to_csv(base_csv_path, store_status, output_csv_path, years)
        
        logger.info(f"\n{'='*60}")
        logger.info("CSV 파일 비교 완료!")
        logger.info(f"{'='*60}")
        logger.info(f"결과 파일: {output_csv_path}")


if __name__ == "__main__":
    main()

