"""성수동 골목길 유동인구 데이터 종합 수집 스크립트
- 성수동 좌표 범위 순회
- 요일/연령대/시간대별 조합 수집
- 중복 데이터 정제
"""

import sys
import time
import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 프로젝트 루트를 sys.path에 추가
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.foottraffic.scraper import FoottrafficScraper
from config.scrapers.foottraffic import FoottrafficConfig
from core.logger import get_logger
from core.file_handler import FileHandler

# pyproj import (GeoJSON 좌표 변환용)
try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

logger = get_logger(__name__)


# 성수동 좌표 범위 (2025년 3분기 기준) - 설정 파일에서 가져옴
SEONGSU_BOUNDS = FoottrafficConfig.get_seongsu_bounds()

# 격자 크기 (좌표 단위) - 필요시 조정 가능
GRID_SIZE_X = 100.0  # 약 100m
GRID_SIZE_Y = 100.0  # 약 100m

# 요일 옵션
DAYWEEK_OPTIONS = [
    (1, "주중"),
    (2, "주말")
]

# 연령대 옵션
# 문서: agrde : (전체)00, (10대)10, (20대)20, (30대)30, (40대)40, (50대)50, (60대이상)60
# 문자열 형식으로 전송해야 함
AGRDE_OPTIONS = [
    ("00", "전체"),
    ("10", "10대"),
    ("20", "20대"),
    ("30", "30대"),
    ("40", "40대"),
    ("50", "50대"),
    ("60", "60대이상"),
]

# 시간대 옵션
TMZON_OPTIONS = [
    ("00", "종일"),
    ("01", "00~05"),
    ("02", "06~10"),
    ("03", "11~13"),
    ("04", "14~16"),
    ("05", "17~20"),
    ("06", "21~23")
]


def generate_grid_bounds(bounds: Dict[str, float], grid_size_x: float, grid_size_y: float) -> List[Dict[str, float]]:
    """좌표 범위를 격자로 나누어 반환
    
    Args:
        bounds: 전체 좌표 범위 (minx, miny, maxx, maxy)
        grid_size_x: X축 격자 크기
        grid_size_y: Y축 격자 크기
        
    Returns:
        격자별 좌표 범위 리스트
    """
    grid_bounds = []
    
    minx = bounds['minx']
    miny = bounds['miny']
    maxx = bounds['maxx']
    maxy = bounds['maxy']
    
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            grid_bounds.append({
                'minx': x,
                'miny': y,
                'maxx': min(x + grid_size_x, maxx),
                'maxy': min(y + grid_size_y, maxy)
            })
            y += grid_size_y
        x += grid_size_x
    
    return grid_bounds


# ============================================================================
# GeoJSON 변환 함수 (convert_wkt_to_geojson.py에서 통합)
# ============================================================================

def parse_wkt_linestring(wkt_string):
    """WKT LINESTRING 문자열을 좌표 리스트로 파싱
    
    Args:
        wkt_string: WKT 형식의 LINESTRING 문자열
        예: "LINESTRING (204369.0 449890.11, 204380.21 449896.98)"
        
    Returns:
        좌표 리스트 [[x1, y1], [x2, y2], ...]
    """
    if not wkt_string or not isinstance(wkt_string, str):
        return None
    
    # LINESTRING (x1 y1, x2 y2, ...) 형식 파싱
    wkt_string = wkt_string.strip()
    
    # LINESTRING 키워드 제거
    if wkt_string.upper().startswith('LINESTRING'):
        # LINESTRING ( ... ) 형식
        match_start = wkt_string.find('(')
        match_end = wkt_string.rfind(')')
        if match_start == -1 or match_end == -1:
            return None
        coords_str = wkt_string[match_start + 1:match_end]
    else:
        # 이미 좌표만 있는 경우
        coords_str = wkt_string
    
    # 좌표 파싱
    coords = []
    for coord_pair in coords_str.split(','):
        coord_pair = coord_pair.strip()
        if not coord_pair:
            continue
        
        parts = coord_pair.split()
        if len(parts) >= 2:
            try:
                x = float(parts[0])
                y = float(parts[1])
                coords.append([x, y])
            except ValueError:
                logger.warning(f"좌표 파싱 실패: {coord_pair}")
                continue
    
    return coords if coords else None


def utm_k_to_wgs84(x, y, transformer=None):
    """UTM-K 좌표를 WGS84로 변환
    
    Args:
        x: UTM-K X 좌표
        y: UTM-K Y 좌표
        transformer: pyproj Transformer 객체 (없으면 None 반환)
        
    Returns:
        [경도, 위도] 또는 None (변환 실패 시)
    """
    if transformer is None:
        return None
    
    try:
        lon, lat = transformer.transform(x, y)
        return [lon, lat]
    except Exception as e:
        logger.warning(f"좌표 변환 실패 ({x}, {y}): {e}")
        return None


def wkt_to_geojson_feature(wkt_string, properties, transformer=None):
    """WKT LINESTRING을 GeoJSON Feature로 변환
    
    Args:
        wkt_string: WKT 형식의 LINESTRING 문자열
        properties: Feature의 properties 딕셔너리
        transformer: 좌표 변환기 (None이면 변환 없이 UTM-K 좌표 사용)
        
    Returns:
        GeoJSON Feature 객체 또는 None
    """
    coords = parse_wkt_linestring(wkt_string)
    if not coords:
        return None
    
    # 좌표 변환 (transformer가 있으면 WGS84로, 없으면 UTM-K 그대로)
    if transformer:
        converted_coords = []
        for x, y in coords:
            wgs84_coord = utm_k_to_wgs84(x, y, transformer)
            if wgs84_coord:
                converted_coords.append(wgs84_coord)
            else:
                # 변환 실패 시 원본 좌표 사용
                converted_coords.append([x, y])
        
        if not converted_coords:
            return None
        coords = converted_coords
    
    return {
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': coords
        },
        'properties': properties
    }


def convert_csv_to_geojson(csv_path, output_path=None, convert_coords=True):
    """CSV 파일을 GeoJSON으로 변환
    
    Args:
        csv_path: 입력 CSV 파일 경로
        output_path: 출력 GeoJSON 파일 경로 (None이면 자동 생성)
        convert_coords: 좌표 변환 여부 (UTM-K → WGS84)
        
    Returns:
        생성된 GeoJSON 파일 경로
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
    
    # 좌표 변환기 초기화
    transformer = None
    if convert_coords and HAS_PYPROJ:
        try:
            # UTM-K (EPSG:5181, 한국 중부원점) → WGS84 (EPSG:4326) 변환기
            # EPSG:5181은 한국 중부원점 UTM-K 좌표계 (서울 지역 포함)
            transformer = Transformer.from_crs("EPSG:5181", "EPSG:4326", always_xy=True)
            logger.info("좌표 변환기 초기화 완료 (UTM-K EPSG:5181 → WGS84)")
        except Exception as e:
            logger.warning(f"좌표 변환기 초기화 실패: {e}. 좌표 변환 없이 진행합니다.")
            transformer = None
    elif convert_coords and not HAS_PYPROJ:
        logger.warning("pyproj가 설치되지 않아 좌표 변환 없이 진행합니다.")
        logger.warning("UTM-K 좌표를 그대로 사용합니다. (GeoJSON 표준은 WGS84입니다)")
    
    # 출력 파일 경로 생성
    if output_path is None:
        output_dir = csv_path.parent
        output_filename = csv_path.stem + '_geojson.geojson'
        output_path = output_dir / output_filename
    else:
        output_path = Path(output_path)
        # 확장자가 없거나 .json인 경우 .geojson으로 변경
        if output_path.suffix == '' or output_path.suffix == '.json':
            output_path = output_path.with_suffix('.geojson')
    
    # CSV 읽기
    logger.info(f"CSV 파일 읽기: {csv_path}")
    features = []
    skipped_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # 헤더 제외, 2부터 시작
            wkt = row.get('wkt', '').strip()
            if not wkt:
                skipped_count += 1
                continue
            
            # properties 생성 (wkt 필드 제외)
            properties = {k: v for k, v in row.items() if k != 'wkt'}
            
            # GeoJSON Feature 생성
            feature = wkt_to_geojson_feature(wkt, properties, transformer)
            if feature:
                features.append(feature)
            else:
                skipped_count += 1
                logger.debug(f"행 {row_num} 변환 실패: {wkt[:50]}...")
    
    logger.info(f"변환 완료: {len(features)}개 Feature 생성, {skipped_count}개 건너뜀")
    
    # GeoJSON 생성
    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'source': str(csv_path.name),
            'conversion_time': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'total_features': len(features),
            'coordinate_system': 'WGS84' if transformer else 'UTM-K',
            'skipped_count': skipped_count
        }
    }
    
    # 파일 저장
    logger.info(f"GeoJSON 파일 저장: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 변환 완료: {output_path}")
    logger.info(f"   - 총 {len(features)}개 LineString Feature")
    logger.info(f"   - 좌표계: {geojson['metadata']['coordinate_system']}")
    
    return output_path


# 전역 락 (스레드 안전성)
collection_lock = Lock()

def _process_single_combination(
    grid_idx: int,
    grid_bounds: Dict[str, float],
    dayweek: int,
    dayweek_name: str,
    agrde: str,
    agrde_name: str,
    tmzon: str,
    tmzon_name: str,
    delay: float = 0.0
) -> Tuple[Dict, List[Dict]]:
    """단일 조합 처리 (병렬 처리용)
    
    Args:
        grid_idx: 격자 인덱스
        grid_bounds: 격자 좌표 범위
        dayweek: 요일 코드
        dayweek_name: 요일 이름
        agrde: 연령대 코드
        agrde_name: 연령대 이름
        tmzon: 시간대 코드
        tmzon_name: 시간대 이름
        delay: API 호출 간 지연 시간 (초)
        
    Returns:
        (통계 정보, 레코드 리스트)
    """
    # 각 스레드마다 독립적인 scraper 인스턴스 생성
    scraper = FoottrafficScraper()
    
    try:
        # API 호출
        result = scraper.scrape(
            minx=grid_bounds['minx'],
            miny=grid_bounds['miny'],
            maxx=grid_bounds['maxx'],
            maxy=grid_bounds['maxy'],
            dayweek=dayweek,
            agrde=agrde,
            tmzon=tmzon,
            use_seongsu_bounds=False,
            save_json=False,
            save_csv=False
        )
        
        # 데이터 수집
        records = result['data'].get('records', [])
        
        # 각 레코드에 메타데이터 추가
        for record in records:
            record['_metadata'] = {
                'dayweek': dayweek,
                'dayweek_name': dayweek_name,
                'agrde': agrde,
                'agrde_name': agrde_name,
                'tmzon': tmzon,
                'tmzon_name': tmzon_name,
                'grid_idx': grid_idx,
                'bounds': grid_bounds
            }
        
        # 통계 정보
        stats = {
            'grid_idx': grid_idx,
            'bounds': grid_bounds,
            'dayweek': dayweek,
            'agrde': agrde,
            'tmzon': tmzon,
            'record_count': len(records),
            'success': True
        }
        
        return stats, records
        
    except Exception as e:
        logger.error(f"조합 처리 실패 (격자{grid_idx}, {dayweek_name}/{agrde_name}/{tmzon_name}): {e}")
        stats = {
            'grid_idx': grid_idx,
            'bounds': grid_bounds,
            'dayweek': dayweek,
            'agrde': agrde,
            'tmzon': tmzon,
            'record_count': 0,
            'success': False,
            'error': str(e)
        }
        return stats, []
    finally:
        scraper.close()
        # 지연 시간 적용
        if delay > 0:
            time.sleep(delay)


def collect_with_combinations(
    scraper: FoottrafficScraper,
    bounds: Dict[str, float],
    use_grid: bool = False,
    delay: float = 0.5,
    use_parallel: bool = True,
    max_workers: int = 5
) -> Dict[str, any]:
    """모든 조합(요일/연령대/시간대)으로 데이터 수집
    
    Args:
        scraper: FoottrafficScraper 인스턴스 (병렬 모드에서는 사용되지 않음)
        bounds: 좌표 범위
        use_grid: 격자로 나누어 수집할지 여부
        delay: API 호출 간 지연 시간 (초, 병렬 모드에서는 각 작업 후 적용)
        use_parallel: 병렬 처리 여부
        max_workers: 병렬 처리 시 최대 워커 수
        
    Returns:
        수집된 데이터와 통계 정보
    """
    all_records = []
    collection_stats = {
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'total_records': 0,
        'unique_roadlinks': set(),
        'combinations': []
    }
    
    # 격자 생성 또는 전체 영역 사용
    if use_grid:
        grid_bounds_list = generate_grid_bounds(bounds, GRID_SIZE_X, GRID_SIZE_Y)
        logger.info(f"격자로 나누어 수집: {len(grid_bounds_list)}개 격자")
    else:
        grid_bounds_list = [bounds]
        logger.info("전체 영역으로 수집")
    
    total_combinations = len(grid_bounds_list) * len(DAYWEEK_OPTIONS) * len(AGRDE_OPTIONS) * len(TMZON_OPTIONS)
    
    logger.info(f"총 조합 수: {total_combinations}개")
    logger.info(f"병렬 처리: {'활성화' if use_parallel else '비활성화'}")
    if use_parallel:
        logger.info(f"최대 워커 수: {max_workers}개")
    logger.info("=" * 80)
    
    # 모든 조합 생성
    tasks = []
    for grid_idx, grid_bounds in enumerate(grid_bounds_list):
        for dayweek, dayweek_name in DAYWEEK_OPTIONS:
            for agrde, agrde_name in AGRDE_OPTIONS:
                for tmzon, tmzon_name in TMZON_OPTIONS:
                    tasks.append({
                        'grid_idx': grid_idx,
                        'grid_bounds': grid_bounds,
                        'dayweek': dayweek,
                        'dayweek_name': dayweek_name,
                        'agrde': agrde,
                        'agrde_name': agrde_name,
                        'tmzon': tmzon,
                        'tmzon_name': tmzon_name
                    })
    
    if use_parallel:
        # 병렬 처리
        completed = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_task = {
                executor.submit(
                    _process_single_combination,
                    task['grid_idx'],
                    task['grid_bounds'],
                    task['dayweek'],
                    task['dayweek_name'],
                    task['agrde'],
                    task['agrde_name'],
                    task['tmzon'],
                    task['tmzon_name'],
                    delay
                ): task
                for task in tasks
            }
            
            # 완료된 작업 처리
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    stats, records = future.result()
                    
                    # 스레드 안전하게 데이터 수집
                    with collection_lock:
                        if stats['success']:
                            all_records.extend(records)
                            collection_stats['successful_requests'] += 1
                            collection_stats['total_records'] += len(records)
                            
                            for record in records:
                                collection_stats['unique_roadlinks'].add(record.get('roadLinkId'))
                        else:
                            collection_stats['failed_requests'] += 1
                        
                        collection_stats['combinations'].append({
                            'grid_idx': stats['grid_idx'],
                            'bounds': stats['bounds'],
                            'dayweek': stats['dayweek'],
                            'agrde': stats['agrde'],
                            'tmzon': stats['tmzon'],
                            'record_count': stats['record_count']
                        })
                        collection_stats['total_requests'] += 1
                    
                    completed += 1
                    
                    # 진행 상황 로깅
                    if completed % 10 == 0 or completed == total_combinations:
                        elapsed = time.time() - start_time
                        progress_pct = (completed / total_combinations) * 100
                        rate = completed / elapsed if elapsed > 0 else 0
                        remaining = (total_combinations - completed) / rate if rate > 0 else 0
                        
                        logger.info(f"[{completed}/{total_combinations} ({progress_pct:.1f}%)] "
                                  f"속도: {rate:.1f}개/초, 예상 남은 시간: {remaining/60:.1f}분")
                    
                except Exception as e:
                    logger.error(f"작업 처리 중 오류: {e}")
                    with collection_lock:
                        collection_stats['failed_requests'] += 1
                        collection_stats['total_requests'] += 1
    else:
        # 순차 처리 (기존 방식)
        current_combination = 0
        for grid_idx, grid_bounds in enumerate(grid_bounds_list):
            logger.info(f"\n[격자 {grid_idx + 1}/{len(grid_bounds_list)}] "
                       f"범위: ({grid_bounds['minx']:.2f}, {grid_bounds['miny']:.2f}) ~ "
                       f"({grid_bounds['maxx']:.2f}, {grid_bounds['maxy']:.2f})")
            
            for dayweek, dayweek_name in DAYWEEK_OPTIONS:
                for agrde, agrde_name in AGRDE_OPTIONS:
                    for tmzon, tmzon_name in TMZON_OPTIONS:
                        current_combination += 1
                        combination_info = f"{dayweek_name}/{agrde_name}/{tmzon_name}"
                        
                        logger.info(f"  [{current_combination}/{total_combinations}] {combination_info}...")
                        
                        try:
                            result = scraper.scrape(
                                minx=grid_bounds['minx'],
                                miny=grid_bounds['miny'],
                                maxx=grid_bounds['maxx'],
                                maxy=grid_bounds['maxy'],
                                dayweek=dayweek,
                                agrde=agrde,
                                tmzon=tmzon,
                                use_seongsu_bounds=False,
                                save_json=False,
                                save_csv=False
                            )
                            
                            records = result['data'].get('records', [])
                            if records:
                                for record in records:
                                    record['_metadata'] = {
                                        'dayweek': dayweek,
                                        'dayweek_name': dayweek_name,
                                        'agrde': agrde,
                                        'agrde_name': agrde_name,
                                        'tmzon': tmzon,
                                        'tmzon_name': tmzon_name,
                                        'grid_idx': grid_idx,
                                        'bounds': grid_bounds
                                    }
                                    all_records.append(record)
                                    collection_stats['unique_roadlinks'].add(record.get('roadLinkId'))
                                
                                logger.info(f"    -> {len(records)}개 레코드 수집")
                                collection_stats['successful_requests'] += 1
                                collection_stats['total_records'] += len(records)
                            else:
                                logger.info(f"    -> 0개 레코드")
                                collection_stats['successful_requests'] += 1
                            
                            collection_stats['combinations'].append({
                                'grid_idx': grid_idx,
                                'bounds': grid_bounds,
                                'dayweek': dayweek,
                                'agrde': agrde,
                                'tmzon': tmzon,
                                'record_count': len(records)
                            })
                            
                        except Exception as e:
                            logger.error(f"    -> 오류 발생: {e}")
                            collection_stats['failed_requests'] += 1
                        
                        collection_stats['total_requests'] += 1
                        
                        if delay > 0:
                            time.sleep(delay)
    
    collection_stats['unique_roadlinks'] = len(collection_stats['unique_roadlinks'])
    
    return {
        'records': all_records,
        'stats': collection_stats
    }


def deduplicate_records(records: List[Dict]) -> Tuple[List[Dict], Dict]:
    """중복 레코드 정제
    
    요일/연령대/시간대별로 구분된 데이터를 유지하면서,
    같은 조합(roadLinkId + dayweek + agrde + tmzon) 내에서만 중복 제거
    
    Args:
        records: 원본 레코드 리스트
        
    Returns:
        (정제된 레코드 리스트, 정제 통계)
    """
    dedup_stats = {
        'total_records': len(records),
        'duplicate_count': 0,
        'unique_count': 0,
        'duplicate_by_combination': {}
    }
    
    # 조합 키를 기준으로 그룹화 (roadLinkId + dayweek + agrde + tmzon)
    combination_groups = {}
    for record in records:
        metadata = record.get('_metadata', {})
        roadlink_id = record.get('roadLinkId')
        dayweek = metadata.get('dayweek')
        agrde = metadata.get('agrde')
        tmzon = metadata.get('tmzon')
        
        # 고유 조합 키 생성
        combination_key = f"{roadlink_id}_{dayweek}_{agrde}_{tmzon}"
        
        if combination_key not in combination_groups:
            combination_groups[combination_key] = []
        combination_groups[combination_key].append(record)
    
    # 중복 제거: 각 조합별로 하나의 레코드만 선택
    deduplicated = []
    for combination_key, group in combination_groups.items():
        if len(group) > 1:
            # 같은 조합 내에서 중복이 있는 경우: cost 값이 가장 높은 레코드 선택
            best_record = max(group, key=lambda r: r.get('cost', 0))
            deduplicated.append(best_record)
            dedup_stats['duplicate_by_combination'][combination_key] = len(group) - 1
            dedup_stats['duplicate_count'] += len(group) - 1
        else:
            deduplicated.append(group[0])
    
    dedup_stats['unique_count'] = len(deduplicated)
    
    return deduplicated, dedup_stats


def main(use_grid: bool = False, delay: float = 0.5, convert_to_geojson: bool = True, use_parallel: bool = True, max_workers: int = 5):
    """메인 함수
    
    Args:
        use_grid: 격자로 나누어 수집할지 여부 (기본값: False - 전체 영역)
        delay: API 호출 간 지연 시간 (초, 기본값: 0.5, 병렬 모드에서는 각 작업 후 적용)
        convert_to_geojson: GeoJSON 변환 여부 (기본값: True)
        use_parallel: 병렬 처리 여부 (기본값: True)
        max_workers: 병렬 처리 시 최대 워커 수 (기본값: 5)
    """
    logger.info("=" * 80)
    logger.info("성수동 골목길 유동인구 데이터 종합 수집 시작")
    logger.info("=" * 80)
    logger.info(f"수집 모드: {'격자 순회' if use_grid else '전체 영역'}")
    logger.info(f"API 호출 지연: {delay}초")
    logger.info(f"요일: {len(DAYWEEK_OPTIONS)}개")
    logger.info(f"연령대: {len(AGRDE_OPTIONS)}개")
    logger.info(f"시간대: {len(TMZON_OPTIONS)}개")
    
    try:
        # 스크래퍼 초기화
        scraper = FoottrafficScraper()
        
        # 데이터 수집
        start_time = time.time()
        collection_result = collect_with_combinations(
            scraper=scraper,
            bounds=SEONGSU_BOUNDS,
            use_grid=use_grid,
            delay=delay,
            use_parallel=use_parallel,
            max_workers=max_workers
        )
        collection_time = time.time() - start_time
        
        all_records = collection_result['records']
        collection_stats = collection_result['stats']
        
        logger.info("\n" + "=" * 80)
        logger.info("수집 완료 - 중복 제거 시작")
        logger.info("=" * 80)
        
        # 중복 제거
        deduplicated_records, dedup_stats = deduplicate_records(all_records)
        
        logger.info("\n" + "=" * 80)
        logger.info("수집 및 정제 완료")
        logger.info("=" * 80)
        logger.info(f"수집 시간: {collection_time:.2f}초")
        logger.info(f"\n[수집 통계]")
        logger.info(f"  총 요청 수: {collection_stats['total_requests']}개")
        logger.info(f"  성공: {collection_stats['successful_requests']}개")
        logger.info(f"  실패: {collection_stats['failed_requests']}개")
        logger.info(f"  수집된 레코드: {collection_stats['total_records']}개")
        logger.info(f"  고유 도로 링크: {collection_stats['unique_roadlinks']}개")
        logger.info(f"\n[정제 통계]")
        logger.info(f"  원본 레코드: {dedup_stats['total_records']}개")
        logger.info(f"  중복 제거: {dedup_stats['duplicate_count']}개")
        logger.info(f"  최종 레코드: {dedup_stats['unique_count']}개")
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data/raw/foottraffic") / f"foottraffic_seongsu_comprehensive_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 원본 데이터 저장 (메타데이터 포함)
        raw_data = {
            'metadata': {
                'collection_time': timestamp,
                'bounds': SEONGSU_BOUNDS,
                'use_grid': use_grid,
                'grid_size': {'x': GRID_SIZE_X, 'y': GRID_SIZE_Y} if use_grid else None,
                'collection_stats': collection_stats,
                'dedup_stats': dedup_stats
            },
            'records': all_records
        }
        
        raw_json_path = output_dir / f"foottraffic_seongsu_raw_{timestamp}.json"
        FileHandler.save_json(raw_data, raw_json_path)
        logger.info(f"\n원본 데이터 저장: {raw_json_path}")
        
        # 정제된 데이터 저장 (메타데이터를 일반 필드로 변환)
        cleaned_records = []
        for record in deduplicated_records:
            cleaned_record = {k: v for k, v in record.items() if not k.startswith('_')}
            
            # 메타데이터를 일반 필드로 추가
            metadata = record.get('_metadata', {})
            if metadata:
                cleaned_record['dayweek'] = metadata.get('dayweek')
                cleaned_record['dayweek_name'] = metadata.get('dayweek_name')
                cleaned_record['agrde'] = metadata.get('agrde')
                cleaned_record['agrde_name'] = metadata.get('agrde_name')
                cleaned_record['tmzon'] = metadata.get('tmzon')
                cleaned_record['tmzon_name'] = metadata.get('tmzon_name')
            
            cleaned_records.append(cleaned_record)
        
        cleaned_data = {
            'metadata': {
                'collection_time': timestamp,
                'bounds': SEONGSU_BOUNDS,
                'use_grid': use_grid,
                'total_records': len(cleaned_records),
                'collection_stats': collection_stats,
                'dedup_stats': dedup_stats
            },
            'records': cleaned_records
        }
        
        cleaned_json_path = output_dir / f"foottraffic_seongsu_cleaned_{timestamp}.json"
        cleaned_csv_path = output_dir / f"foottraffic_seongsu_cleaned_{timestamp}.csv"
        
        FileHandler.save_json(cleaned_data, cleaned_json_path)
        FileHandler.save_csv(cleaned_records, cleaned_csv_path)
        
        logger.info(f"정제된 데이터 저장:")
        logger.info(f"  JSON: {cleaned_json_path}")
        logger.info(f"  CSV: {cleaned_csv_path}")
        
        # GeoJSON 변환 (선택적)
        cleaned_geojson_path = None
        if convert_to_geojson:
            try:
                logger.info("\n" + "=" * 80)
                logger.info("GeoJSON 변환 시작")
                logger.info("=" * 80)
                
                cleaned_geojson_path = convert_csv_to_geojson(
                    csv_path=cleaned_csv_path,
                    output_path=None,  # 자동 생성 (CSV 파일명 기반)
                    convert_coords=True  # UTM-K → WGS84 변환
                )
                
                logger.info(f"GeoJSON 파일 생성 완료: {cleaned_geojson_path}")
            except Exception as e:
                logger.warning(f"GeoJSON 변환 실패 (계속 진행): {e}")
                cleaned_geojson_path = None
        
        # 스크래퍼 종료
        scraper.close()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 작업 완료!")
        logger.info("=" * 80)
        
        result = {
            'raw_path': str(raw_json_path),
            'cleaned_json_path': str(cleaned_json_path),
            'cleaned_csv_path': str(cleaned_csv_path),
            'stats': {
                'collection': collection_stats,
                'deduplication': dedup_stats
            }
        }
        
        if cleaned_geojson_path:
            result['cleaned_geojson_path'] = str(cleaned_geojson_path)
        
        return result
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="성수동 골목길 유동인구 데이터 종합 수집")
    parser.add_argument('--use-grid', action='store_true', help='격자로 나누어 수집')
    parser.add_argument('--delay', type=float, default=0.3, help='API 호출 간 지연 시간 (초, 기본값: 0.3)')
    parser.add_argument('--no-geojson', action='store_true', help='GeoJSON 변환 건너뛰기')
    parser.add_argument('--no-parallel', action='store_true', help='병렬 처리 비활성화 (순차 처리)')
    parser.add_argument('--max-workers', type=int, default=5, help='병렬 처리 시 최대 워커 수 (기본값: 5)')
    
    args = parser.parse_args()
    
    main(
        use_grid=args.use_grid,
        delay=args.delay,
        convert_to_geojson=not args.no_geojson,
        use_parallel=not args.no_parallel,
        max_workers=args.max_workers
    )

