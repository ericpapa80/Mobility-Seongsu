"""SGIS 기술업종 통계지도 연도별 시계열 데이터 수집 스크립트 (좌표 변환 포함)"""

import sys
import json
import csv
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
# 스크립트 위치: scripts/sgis/collection/run_sgis_timeseries.py
# 프로젝트 루트: scripts/sgis/collection/ -> scripts/sgis/ -> scripts/ -> 프로젝트 루트
script_dir = Path(__file__).resolve().parent  # scripts/sgis/collection/
project_root = script_dir.parent.parent.parent  # 프로젝트 루트
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.sgis.scraper import SGISScraper
from core.logger import get_logger

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False
    print("⚠️ 경고: pyproj가 설치되지 않았습니다. 좌표 변환을 건너뜁니다.")
    print("   설치: pip install pyproj")

logger = get_logger(__name__)


def convert_coordinates_to_wgs84(data: dict, json_path: Path, csv_path: Path = None, year: int = None) -> dict:
    """EPSG:5179 좌표를 EPSG:4326 (WGS84)로 변환하여 새 파일로 저장.
    
    Args:
        data: 원본 데이터 (result 키 포함)
        json_path: 원본 JSON 파일 경로
        csv_path: 원본 CSV 파일 경로 (선택)
        year: 연도 (파일명 및 컬럼에 추가)
        
    Returns:
        변환된 파일 경로 딕셔너리
    """
    if not HAS_PYPROJ:
        logger.warning("pyproj가 없어 좌표 변환을 건너뜁니다.")
        return {}
    
    # 좌표 변환기 생성
    transformer = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
    
    items = data.get('result', [])
    if not items:
        logger.warning("변환할 데이터가 없습니다.")
        return {}
    
    converted_count = 0
    error_count = 0
    
    # 좌표 변환
    for item in items:
        try:
            x = float(item.get('x', 0))
            y = float(item.get('y', 0))
            
            # 연도 컬럼 추가
            if year is not None and 'year' not in item:
                item['year'] = year
            
            if x > 0 and y > 0:
                # EPSG:5179 → EPSG:4326 변환
                lon, lat = transformer.transform(x, y)
                
                # 원본 좌표는 유지하고, 새로운 필드에 WGS84 좌표 추가
                item['x_5179'] = item.get('x')  # 원본 좌표 보존
                item['y_5179'] = item.get('y')  # 원본 좌표 보존
                item['x'] = f"{lon:.6f}"  # 경도 (longitude)
                item['y'] = f"{lat:.6f}"  # 위도 (latitude)
                item['lon'] = f"{lon:.6f}"  # 경도 별칭
                item['lat'] = f"{lat:.6f}"  # 위도 별칭
                
                converted_count += 1
            else:
                error_count += 1
                item['x_5179'] = item.get('x')
                item['y_5179'] = item.get('y')
                
        except Exception as e:
            error_count += 1
            logger.warning(f"좌표 변환 오류: {e}")
            item['x_5179'] = item.get('x')
            item['y_5179'] = item.get('y')
    
    logger.info(f"좌표 변환 완료: {converted_count}개 성공, {error_count}개 오류")
    
    # WGS84 변환된 파일 저장
    result_files = {}
    
    # JSON 저장 (연도는 원본 파일명에 이미 포함됨)
    wgs84_json_path = json_path.parent / f"{json_path.stem}_wgs84.json"
    with open(wgs84_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    result_files['wgs84_json'] = str(wgs84_json_path)
    logger.info(f"WGS84 JSON 저장: {wgs84_json_path}")
    
    # CSV 저장 (연도는 원본 파일명에 이미 포함됨)
    if csv_path and items:
        wgs84_csv_path = csv_path.parent / f"{csv_path.stem}_wgs84.csv"
        fieldnames = list(items[0].keys())
        with open(wgs84_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(items)
        result_files['wgs84_csv'] = str(wgs84_csv_path)
        logger.info(f"WGS84 CSV 저장: {wgs84_csv_path}")
    
    return result_files


def main():
    """연도별 시계열 데이터 수집"""
    
    # 수집할 연도 범위
    years = list(range(2016, 2024))  # 2016~2023
    
    # 행정구역 코드 (성동구)
    adm_cd = "11040"
    
    # 테마 코드 (0 = 전체)
    theme_cd = 0
    
    print("=" * 80)
    print("SGIS 기술업종 통계지도 연도별 시계열 데이터 수집")
    print("=" * 80)
    print(f"수집 기간: {years[0]}년 ~ {years[-1]}년 (총 {len(years)}개 연도)")
    print(f"행정구역: 성동구 (adm_cd={adm_cd})")
    print(f"테마 코드: {theme_cd} (전체 기술업종)")
    print()
    
    scraper = SGISScraper()
    results = {}
    
    try:
        for year in years:
            print(f"\n{'='*80}")
            print(f"{year}년 데이터 수집 중...")
            print(f"{'='*80}")
            
            try:
                result = scraper.scrape(
                    theme_cd=theme_cd,
                    year=year,
                    adm_cd=adm_cd,
                    data_type=3,
                    save_json=True,
                    save_csv=True
                )
                
                # 결과 저장
                data = result.get('data', {})
                items = data.get('result', [])
                
                results[year] = {
                    'success': True,
                    'count': len(items) if items else 0,
                    'timestamp': result.get('timestamp'),
                    'files': result.get('files', {})
                }
                
                print(f"✅ {year}년 수집 완료: {len(items)}개 항목")
                if 'files' in result:
                    if 'json' in result['files']:
                        print(f"   JSON: {result['files']['json']}")
                    if 'csv' in result['files']:
                        print(f"   CSV: {result['files']['csv']}")
                
                # 좌표 변환 (WGS84)
                print(f"\n   좌표 변환 중 (EPSG:5179 → EPSG:4326)...")
                json_path = Path(result['files'].get('json', ''))
                csv_path = Path(result['files'].get('csv', '')) if 'csv' in result['files'] else None
                
                if json_path.exists():
                    wgs84_files = convert_coordinates_to_wgs84(data, json_path, csv_path, year=year)
                    if wgs84_files:
                        results[year]['wgs84_files'] = wgs84_files
                        if 'wgs84_json' in wgs84_files:
                            print(f"   WGS84 JSON: {wgs84_files['wgs84_json']}")
                        if 'wgs84_csv' in wgs84_files:
                            print(f"   WGS84 CSV: {wgs84_files['wgs84_csv']}")
                else:
                    print(f"   ⚠️ JSON 파일을 찾을 수 없어 좌표 변환을 건너뜁니다.")
                
            except Exception as e:
                logger.error(f"{year}년 데이터 수집 실패: {e}")
                results[year] = {
                    'success': False,
                    'error': str(e),
                    'count': 0
                }
                print(f"❌ {year}년 수집 실패: {e}")
            
            # API 부하 방지를 위한 대기 (연도 간)
            if year < years[-1]:
                print("다음 연도 수집을 위해 2초 대기...")
                time.sleep(2)
        
    finally:
        scraper.close()
    
    # 최종 요약
    print("\n" + "=" * 80)
    print("수집 완료 요약")
    print("=" * 80)
    
    success_count = sum(1 for r in results.values() if r.get('success', False))
    total_count = sum(r.get('count', 0) for r in results.values())
    
    print(f"총 연도: {len(years)}개")
    print(f"성공: {success_count}개")
    print(f"실패: {len(years) - success_count}개")
    print(f"총 수집 항목: {total_count:,}개")
    
    print("\n연도별 상세:")
    for year in years:
        result = results.get(year, {})
        if result.get('success'):
            print(f"  {year}년: ✅ {result.get('count', 0):,}개 항목")
        else:
            print(f"  {year}년: ❌ 실패 - {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("저장 위치")
    print("=" * 80)
    print("원본 데이터 (EPSG:5179): data/raw/sgis/{timestamp}/")
    print("변환된 데이터 (WGS84): data/raw/sgis/{timestamp}/*_wgs84.json, *_wgs84.csv")
    print("=" * 80)
    
    # WGS84 변환 통계
    wgs84_count = sum(1 for r in results.values() if r.get('success') and 'wgs84_files' in r)
    if wgs84_count > 0:
        print(f"\n좌표 변환 완료: {wgs84_count}개 연도")
        print("변환된 파일에는 다음 필드가 포함됩니다:")
        print("  - x, y: EPSG:4326 (WGS84) 좌표 (경도, 위도)")
        print("  - lon, lat: 경도, 위도 별칭")
        print("  - x_5179, y_5179: 원본 EPSG:5179 좌표 (보존)")


if __name__ == "__main__":
    main()

