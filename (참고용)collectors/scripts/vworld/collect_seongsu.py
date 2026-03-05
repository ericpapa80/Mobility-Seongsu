"""성수동 영역 VWorld WFS 2.0 데이터 수집 스크립트

- 도로명주소건물 (lt_c_spbd)
- LX맵 (lt_c_landinfobasemap)

10km² bbox 제한 및 페이지네이션을 고려한 단계별 분할 수집
"""

import sys
import time
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json

# 프로젝트 루트·스크립트 디렉터리를 sys.path에 추가
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from plugins.vworld.api_client import VWorldAPIClient
from convert_json_to_geojson import convert_json_to_geojson
from config.scrapers.vworld import VWorldConfig, WFS_LAYER_PROPERTY_NAMES
from core.logger import get_logger
from core.file_handler import FileHandler

# pyproj for coordinate transformation
try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False
    logger.warning("pyproj not available. Using approximate coordinate conversion.")

logger = get_logger(__name__)


# 성수동 좌표 범위 (EPSG:4326 - 위경도)
# 참고: scripts/nps/regeocode_with_web_search.py에서 확인된 범위
SEONGSU_BBOX_WGS84 = {
    'min_lon': 127.03,
    'min_lat': 37.53,
    'max_lon': 127.08,
    'max_lat': 37.56
}

# 10km² 제한 및 WFS 타일당 1000건 제한을 고려한 타일 크기
# 타일을 더 잘게 나누어 구석구석 누락 없이 수집
TILE_SIZE_METERS = 500  # 500m (더 촘촘한 수집)


def wgs84_to_epsg3857(lon: float, lat: float) -> Tuple[float, float]:
    """WGS84 (EPSG:4326) 좌표를 EPSG:3857 (Web Mercator)로 변환
    
    Args:
        lon: 경도
        lat: 위도
        
    Returns:
        (x, y) in EPSG:3857
    """
    if HAS_PYPROJ:
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        x, y = transformer.transform(lon, lat)
        return (x, y)
    else:
        # 근사 변환 (간단한 공식)
        # EPSG:3857은 Web Mercator projection
        import math
        x = lon * 20037508.34 / 180.0
        y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
        y = y * 20037508.34 / 180.0
        return (x, y)


def epsg3857_to_wgs84(x: float, y: float) -> Tuple[float, float]:
    """EPSG:3857 좌표를 WGS84 (EPSG:4326)로 변환
    
    Args:
        x: EPSG:3857 X 좌표
        y: EPSG:3857 Y 좌표
        
    Returns:
        (lon, lat) in WGS84
    """
    if HAS_PYPROJ:
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(x, y)
        return (lon, lat)
    else:
        # 근사 변환
        import math
        lon = x / 20037508.34 * 180.0
        lat = y / 20037508.34 * 180.0
        lat = 180.0 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
        return (lon, lat)


def geometry_to_wkt(geometry: Dict[str, Any]) -> str:
    """GeoJSON geometry를 WKT 형식으로 변환
    
    Args:
        geometry: GeoJSON geometry 객체
        
    Returns:
        WKT 문자열
    """
    if not geometry or 'type' not in geometry:
        return ''
    
    geom_type = geometry.get('type', '')
    coordinates = geometry.get('coordinates', [])
    
    try:
        if geom_type == 'Point':
            if len(coordinates) >= 2:
                return f"POINT({coordinates[0]} {coordinates[1]})"
        
        elif geom_type == 'LineString':
            coords_str = ', '.join([f"{c[0]} {c[1]}" for c in coordinates if len(c) >= 2])
            return f"LINESTRING({coords_str})"
        
        elif geom_type == 'Polygon':
            if coordinates and len(coordinates) > 0:
                # 외곽 ring만 사용
                ring = coordinates[0]
                coords_str = ', '.join([f"{c[0]} {c[1]}" for c in ring if len(c) >= 2])
                return f"POLYGON(({coords_str}))"
        
        elif geom_type == 'MultiPolygon':
            polygons = []
            for polygon in coordinates:
                if polygon and len(polygon) > 0:
                    ring = polygon[0]
                    coords_str = ', '.join([f"{c[0]} {c[1]}" for c in ring if len(c) >= 2])
                    polygons.append(f"({coords_str})")
            return f"MULTIPOLYGON({','.join(polygons)})"
        
        elif geom_type == 'MultiLineString':
            lines = []
            for line in coordinates:
                coords_str = ', '.join([f"{c[0]} {c[1]}" for c in line if len(c) >= 2])
                lines.append(f"({coords_str})")
            return f"MULTILINESTRING({','.join(lines)})"
    
    except Exception as e:
        logger.warning(f"WKT 변환 실패: {e}")
    
    return ''


def extract_coordinates_from_geometry(geometry: Dict[str, Any], crs: str = "EPSG:3857") -> Dict[str, Any]:
    """지오메트리에서 좌표 정보 추출 (QGIS 활용용)
    
    Args:
        geometry: GeoJSON geometry 객체
        crs: 좌표계 (기본값: EPSG:3857)
        
    Returns:
        좌표 정보 딕셔너리 (x, y, lon, lat, centroid_x, centroid_y, wkt 등)
    """
    coords_info = {
        'geometry_type': geometry.get('type', '') if geometry else '',
        'x': None,
        'y': None,
        'lon': None,
        'lat': None,
        'centroid_x': None,
        'centroid_y': None,
        'centroid_lon': None,
        'centroid_lat': None,
        'wkt': None
    }
    
    if not geometry or 'coordinates' not in geometry:
        return coords_info
    
    geom_type = geometry.get('type', '')
    coordinates = geometry.get('coordinates', [])
    
    try:
        if geom_type == 'Point':
            # Point: 직접 좌표 사용
            if len(coordinates) >= 2:
                x, y = coordinates[0], coordinates[1]
                coords_info['x'] = x
                coords_info['y'] = y
                coords_info['centroid_x'] = x
                coords_info['centroid_y'] = y
                
                # EPSG:3857을 EPSG:4326으로 변환
                if crs == "EPSG:3857":
                    lon, lat = epsg3857_to_wgs84(x, y)
                    coords_info['lon'] = lon
                    coords_info['lat'] = lat
                    coords_info['centroid_lon'] = lon
                    coords_info['centroid_lat'] = lat
        
        elif geom_type in ['Polygon', 'MultiPolygon']:
            # Polygon/MultiPolygon: 중심점 계산
            all_points = []
            
            if geom_type == 'Polygon':
                # Polygon: 첫 번째 ring의 좌표들
                if coordinates and len(coordinates) > 0:
                    ring = coordinates[0]
                    for coord in ring:
                        if len(coord) >= 2:
                            all_points.append([coord[0], coord[1]])
            elif geom_type == 'MultiPolygon':
                # MultiPolygon: 모든 polygon의 첫 번째 ring
                for polygon in coordinates:
                    if polygon and len(polygon) > 0:
                        ring = polygon[0]
                        for coord in ring:
                            if len(coord) >= 2:
                                all_points.append([coord[0], coord[1]])
            
            if all_points:
                # 중심점 계산 (모든 점의 평균)
                centroid_x = sum(p[0] for p in all_points) / len(all_points)
                centroid_y = sum(p[1] for p in all_points) / len(all_points)
                
                coords_info['centroid_x'] = centroid_x
                coords_info['centroid_y'] = centroid_y
                
                # EPSG:3857을 EPSG:4326으로 변환
                if crs == "EPSG:3857":
                    lon, lat = epsg3857_to_wgs84(centroid_x, centroid_y)
                    coords_info['centroid_lon'] = lon
                    coords_info['centroid_lat'] = lat
                
                # 첫 번째 점도 저장 (참고용)
                if all_points:
                    coords_info['x'] = all_points[0][0]
                    coords_info['y'] = all_points[0][1]
                    if crs == "EPSG:3857":
                        lon, lat = epsg3857_to_wgs84(all_points[0][0], all_points[0][1])
                        coords_info['lon'] = lon
                        coords_info['lat'] = lat
        
        elif geom_type in ['LineString', 'MultiLineString']:
            # LineString: 중점 계산
            all_points = []
            
            if geom_type == 'LineString':
                all_points = [[coord[0], coord[1]] for coord in coordinates if len(coord) >= 2]
            elif geom_type == 'MultiLineString':
                for line in coordinates:
                    all_points.extend([[coord[0], coord[1]] for coord in line if len(coord) >= 2])
            
            if all_points:
                # 중점 계산
                mid_idx = len(all_points) // 2
                centroid_x = all_points[mid_idx][0]
                centroid_y = all_points[mid_idx][1]
                
                coords_info['centroid_x'] = centroid_x
                coords_info['centroid_y'] = centroid_y
                
                # EPSG:3857을 EPSG:4326으로 변환
                if crs == "EPSG:3857":
                    lon, lat = epsg3857_to_wgs84(centroid_x, centroid_y)
                    coords_info['centroid_lon'] = lon
                    coords_info['centroid_lat'] = lat
                
                # 첫 번째 점도 저장
                if all_points:
                    coords_info['x'] = all_points[0][0]
                    coords_info['y'] = all_points[0][1]
                    if crs == "EPSG:3857":
                        lon, lat = epsg3857_to_wgs84(all_points[0][0], all_points[0][1])
                        coords_info['lon'] = lon
                        coords_info['lat'] = lat
        
        # WKT 생성
        coords_info['wkt'] = geometry_to_wkt(geometry)
    
    except Exception as e:
        logger.warning(f"좌표 추출 실패: {e}")
    
    return coords_info


def calculate_bbox_area_km2(bbox: List[float]) -> float:
    """bbox 면적 계산 (km²)
    
    Args:
        bbox: [minX, minY, maxX, maxY] in EPSG:3857
        
    Returns:
        면적 (km²)
    """
    minX, minY, maxX, maxY = bbox
    width_m = maxX - minX
    height_m = maxY - minY
    area_m2 = width_m * height_m
    area_km2 = area_m2 / 1_000_000
    return area_km2


def generate_tiles(bbox_3857: List[float], tile_size_m: float = TILE_SIZE_METERS) -> List[List[float]]:
    """bbox를 타일로 분할
    
    Args:
        bbox_3857: [minX, minY, maxX, maxY] in EPSG:3857
        tile_size_m: 타일 크기 (미터)
        
    Returns:
        타일 bbox 리스트 [[minX, minY, maxX, maxY], ...]
    """
    minX, minY, maxX, maxY = bbox_3857
    tiles = []
    
    x = minX
    while x < maxX:
        y = minY
        while y < maxY:
            tile_maxX = min(x + tile_size_m, maxX)
            tile_maxY = min(y + tile_size_m, maxY)
            
            tile_bbox = [x, y, tile_maxX, tile_maxY]
            area = calculate_bbox_area_km2(tile_bbox)
            
            # 10km² 제한 확인
            if area > 10.0:
                logger.warning(f"Tile area {area:.2f}km² exceeds 10km² limit. Splitting further...")
                # 더 작은 타일로 재귀 분할
                sub_tiles = generate_tiles(tile_bbox, tile_size_m / 2)
                tiles.extend(sub_tiles)
            else:
                tiles.append(tile_bbox)
            
            y += tile_size_m
        x += tile_size_m
    
    return tiles


def collect_layer_with_pagination(
    api_client: VWorldAPIClient,
    layer_id: str,
    bbox: List[float],
    max_page_size: int = 100,
    delay_seconds: float = 0.5
) -> Dict[str, any]:
    """페이지네이션을 고려한 레이어 수집
    
    Args:
        api_client: VWorldAPIClient 인스턴스
        layer_id: 레이어 ID
        bbox: [minX, minY, maxX, maxY] in EPSG:3857
        max_page_size: 페이지당 최대 건수
        delay_seconds: 요청 간 지연 시간
        
    Returns:
        수집된 데이터 통합 결과
    """
    all_features = []
    page = 1
    total_collected = 0
    total_records = 0
    
    logger.info(f"Collecting {layer_id} from bbox {bbox}")

    # 토지(LX맵)·건물(도로명주소)은 모두 WFS로 한 번에 수집
    layer_upper = (layer_id or "").upper()
    if layer_upper in WFS_LAYER_PROPERTY_NAMES:
        try:
            data = api_client.get_features_wfs(
                layer_id=layer_id,
                bbox=bbox,
                max_features=1000,  # VWorld WFS 허용 상한 1000
                property_names=WFS_LAYER_PROPERTY_NAMES[layer_upper],
                output="json"
            )
            if "features" in data:
                all_features = data["features"]
                total_collected = len(all_features)
                total_records = total_collected
                logger.info(f"{layer_id} (WFS): collected {total_collected} features")
        except Exception as e:
            logger.error(f"Error collecting {layer_id} via WFS: {e}")
        return {
            'layer_id': layer_id,
            'bbox': bbox,
            'total_features': total_collected,
            'total_records': total_records,
            'features': all_features
        }
    
    while True:
        try:
            # Data API로 직접 요청
            data = api_client.get_features_data_api(
                layer_id=layer_id,
                bbox=bbox,
                size=max_page_size,
                page=page,
                geometry=True,
                attribute=True,
                crs="EPSG:3857"
            )
            
            # Data API 응답 파싱
            if 'response' in data:
                response = data['response']
                
                if response.get('status') != 'OK':
                    error = response.get('error', {})
                    error_text = error.get('text', 'Unknown error')
                    logger.error(f"API error on page {page}: {error_text}")
                    break
                
                # 레코드 정보
                record = response.get('record', {})
                total_records = int(record.get('total', 0) or 0)
                current_page = int(record.get('currentPage', page) or page)
                total_page = int(record.get('totalPage', 0) or 0)
                
                # totalPage가 없거나 0이면 계산
                if total_page == 0 and total_records > 0:
                    import math
                    total_page = math.ceil(total_records / max_page_size)
                
                # 피처 추출
                result_data = response.get('result', {})
                feature_collection = result_data.get('featureCollection', {})
                features = feature_collection.get('features', [])
                
                all_features.extend(features)
                total_collected += len(features)
                
                logger.info(
                    f"Page {current_page}/{total_page}: "
                    f"Collected {len(features)} features "
                    f"(Total: {total_collected}/{total_records})"
                )
                
                # 더 이상 데이터가 없으면 종료
                if len(features) == 0:
                    break
                
                # 마지막 페이지이면 종료
                if total_page > 0 and current_page >= total_page:
                    break
                
                # total_records를 기준으로도 확인
                if total_records > 0 and total_collected >= total_records:
                    break
                
                page += 1
                
                # API 부하 방지를 위한 지연
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                    
            else:
                logger.warning(f"Unexpected response format on page {page}")
                break
                
        except Exception as e:
            logger.error(f"Error collecting page {page} of {layer_id}: {e}")
            break
    
    logger.info(f"Completed collecting {layer_id}: {total_collected} features")
    
    return {
        'layer_id': layer_id,
        'bbox': bbox,
        'total_features': total_collected,
        'total_records': total_records,
        'features': all_features
    }


def collect_seongsu(
    output_dir: Optional[Path] = None,
    tile_size_m: float = TILE_SIZE_METERS,
    max_page_size: int = 100,
    delay_seconds: float = 0.5,
    layers: Optional[List[str]] = None
) -> Dict[str, any]:
    """성수동 영역 VWorld 데이터 수집
    
    Args:
        output_dir: 출력 디렉토리
        tile_size_m: 타일 크기 (미터, 기본값: 500m)
        max_page_size: 페이지당 최대 건수
        delay_seconds: 요청 간 지연 시간
        layers: 수집할 레이어 리스트 (None이면 기본 레이어 사용)
        
    Returns:
        수집 결과 요약
    """
    if layers is None:
        layers = [
            'LT_C_SPBD',  # 도로명주소건물 (Data API - 대문자)
            'LT_C_LANDINFOBASEMAP'  # LX맵 (Data API - 대문자)
        ]
    
    # 출력 디렉토리 설정
    if output_dir is None:
        base_output_dir = project_root / "data" / "raw" / "vworld"
    else:
        base_output_dir = Path(output_dir)
    
    # 날짜/시간 기반 폴더 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"vworld_seongsu_{timestamp}"
    output_dir = base_output_dir / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # raw/processed는 사용하지 않음. 과거 실행 흔적이 있으면 제거
    for sub in ("raw", "processed"):
        d = output_dir / sub
        if d.exists():
            shutil.rmtree(d)
            logger.debug(f"불필요한 하위 폴더 제거: {d}")
    
    logger.info(f"출력 폴더: {output_dir}")
    
    # 성수동 bbox를 EPSG:3857로 변환
    minX, minY = wgs84_to_epsg3857(SEONGSU_BBOX_WGS84['min_lon'], SEONGSU_BBOX_WGS84['min_lat'])
    maxX, maxY = wgs84_to_epsg3857(SEONGSU_BBOX_WGS84['max_lon'], SEONGSU_BBOX_WGS84['max_lat'])
    
    seongsu_bbox_3857 = [minX, minY, maxX, maxY]
    total_area = calculate_bbox_area_km2(seongsu_bbox_3857)
    
    logger.info("=" * 80)
    logger.info("성수동 VWorld WFS 2.0 데이터 수집 시작")
    logger.info("=" * 80)
    logger.info(f"성수동 전체 bbox (EPSG:3857): {seongsu_bbox_3857}")
    logger.info(f"성수동 전체 면적: {total_area:.2f} km²")
    logger.info(f"타일 크기: {tile_size_m}m ({tile_size_m/1000:.1f}km)")
    logger.info(f"수집 레이어: {layers}")
    logger.info("=" * 80)
    
    # 타일 생성
    tiles = generate_tiles(seongsu_bbox_3857, tile_size_m)
    logger.info(f"생성된 타일 수: {len(tiles)}개")
    
    # API 클라이언트·파일 저장만 사용 (스크래퍼 미사용 → raw/processed 등 중간 폴더 생성 안 함)
    api_client = VWorldAPIClient()
    file_handler = FileHandler()
    
    # 수집 결과 저장
    collection_results = {
        'timestamp': datetime.now().isoformat(),
        'region': 'seongsu',
        'bbox_wgs84': SEONGSU_BBOX_WGS84,
        'bbox_3857': seongsu_bbox_3857,
        'total_area_km2': total_area,
        'tile_size_m': tile_size_m,
        'num_tiles': len(tiles),
        'layers': {},
        'summary': {}
    }
    
    # 각 레이어별 수집
    for layer_id in layers:
        logger.info("")
        logger.info(f"[레이어: {layer_id}] 수집 시작")
        logger.info("-" * 80)
        
        layer_results = {
            'layer_id': layer_id,
            'tiles': [],
            'total_features': 0,
            'all_features': []
        }
        
        # 각 타일별 수집
        for tile_idx, tile_bbox in enumerate(tiles, 1):
            tile_area = calculate_bbox_area_km2(tile_bbox)
            
            logger.info(f"타일 {tile_idx}/{len(tiles)}: bbox={tile_bbox}, 면적={tile_area:.2f}km²")
            
            try:
                tile_result = collect_layer_with_pagination(
                    api_client=api_client,
                    layer_id=layer_id,
                    bbox=tile_bbox,
                    max_page_size=max_page_size,
                    delay_seconds=delay_seconds
                )
                
                tile_info = {
                    'tile_index': tile_idx,
                    'bbox': tile_bbox,
                    'area_km2': tile_area,
                    'num_features': tile_result['total_features']
                }
                layer_results['tiles'].append(tile_info)
                layer_results['total_features'] += tile_result['total_features']
                layer_results['all_features'].extend(tile_result['features'])
                
                logger.info(f"  ✓ 수집 완료: {tile_result['total_features']}개 피처")
                
            except Exception as e:
                logger.error(f"  ✗ 타일 {tile_idx} 수집 실패: {e}")
                tile_info = {
                    'tile_index': tile_idx,
                    'bbox': tile_bbox,
                    'area_km2': tile_area,
                    'error': str(e)
                }
                layer_results['tiles'].append(tile_info)
            
            # 타일 간 지연
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        
        # 레이어별 통합 데이터 저장 (같은 폴더에 저장)
        if layer_results['all_features']:
            layer_name = layer_id.lower().replace('_', '-')
            
            # JSON 저장 (같은 timestamp 사용)
            json_data = {
                'layer_id': layer_id,
                'region': 'seongsu',
                'bbox': seongsu_bbox_3857,
                'total_features': layer_results['total_features'],
                'collection_timestamp': timestamp,
                'features': layer_results['all_features']
            }
            json_file = output_dir / f"seongsu_{layer_name}_{timestamp}.json"
            file_handler.save_json(json_data, json_file)
            logger.info(f"  ✓ JSON 저장: {json_file}")
            
            # GeoJSON 생성 (EPSG:3857 → EPSG:4326, 같은 디렉터리에 .geojson 저장)
            try:
                geojson_file = convert_json_to_geojson(json_file, output_path=None, convert_coords=True)
                logger.info(f"  ✓ GeoJSON 저장: {geojson_file}")
            except Exception as e:
                logger.warning(f"  GeoJSON 변환 건너뜀: {e}")
            
            # CSV 저장 (피처 속성 + 좌표 정보, 같은 timestamp 사용)
            csv_data = []
            for feature in layer_results['all_features']:
                row = feature.get('properties', {}).copy()
                
                # 지오메트리에서 좌표 정보 추출
                if 'geometry' in feature:
                    geometry = feature['geometry']
                    coords_info = extract_coordinates_from_geometry(geometry, crs="EPSG:3857")
                    
                    # 좌표 정보를 CSV 행에 추가
                    row.update({
                        'geometry_type': coords_info.get('geometry_type', ''),
                        'x': coords_info.get('x'),
                        'y': coords_info.get('y'),
                        'lon': coords_info.get('lon'),
                        'lat': coords_info.get('lat'),
                        'centroid_x': coords_info.get('centroid_x'),
                        'centroid_y': coords_info.get('centroid_y'),
                        'centroid_lon': coords_info.get('centroid_lon'),
                        'centroid_lat': coords_info.get('centroid_lat'),
                        'wkt': coords_info.get('wkt')
                    })
                
                csv_data.append(row)
            
            if csv_data:
                csv_file = output_dir / f"seongsu_{layer_name}_{timestamp}.csv"
                file_handler.save_csv(csv_data, csv_file)
                logger.info(f"  ✓ CSV 저장: {csv_file}")
        
        collection_results['layers'][layer_id] = {
            'layer_id': layer_id,
            'tiles': layer_results['tiles'],
            'total_features': layer_results['total_features']
        }
        
        logger.info(f"[레이어: {layer_id}] 수집 완료: 총 {layer_results['total_features']}개 피처")
    
    # 최종 결과 저장
    summary_file = output_dir / f"seongsu_collection_summary_{timestamp}.json"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(collection_results, f, ensure_ascii=False, indent=2)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("수집 완료")
    logger.info("=" * 80)
    logger.info(f"출력 폴더: {output_dir}")
    logger.info(f"요약 파일: {summary_file}")
    
    # 요약 출력
    for layer_id, layer_data in collection_results['layers'].items():
        logger.info(f"{layer_id}: {layer_data['total_features']}개 피처")
    
    api_client.close()
    return collection_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="성수동 VWorld WFS 2.0 데이터 수집")
    parser.add_argument(
        "--output-dir",
        type=str,
        help="출력 디렉토리 (기본값: data/raw/vworld)"
    )
    parser.add_argument(
        "--tile-size",
        type=float,
        default=TILE_SIZE_METERS,
        help=f"타일 크기 (미터, 기본값: {TILE_SIZE_METERS}m)"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="페이지당 최대 건수 (기본값: 100)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="요청 간 지연 시간 (초, 기본값: 0.5)"
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        default=['LT_C_SPBD', 'LT_C_LANDINFOBASEMAP'],
        help="수집할 레이어 (기본값: LT_C_SPBD LT_C_LANDINFOBASEMAP)"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    collect_seongsu(
        output_dir=output_dir,
        tile_size_m=args.tile_size,
        max_page_size=args.page_size,
        delay_seconds=args.delay,
        layers=args.layers
    )
