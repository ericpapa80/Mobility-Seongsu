"""VWorld CSV 파일을 GeoJSON으로 변환하는 스크립트

CSV 파일의 WKT 컬럼을 파싱하여 GeoJSON 형식으로 변환합니다.
좌표계는 EPSG:3857 (Web Mercator)에서 EPSG:4326 (WGS84)로 변환합니다.
"""

import sys
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# CSV 필드 크기 제한 증가 (큰 WKT 필드 처리)
csv.field_size_limit(sys.maxsize)

# 프로젝트 루트를 sys.path에 추가
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import get_logger

# pyproj import (좌표 변환용)
try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

# shapely import (WKT 파싱용, 선택사항)
try:
    from shapely import wkt
    from shapely.geometry import mapping
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

logger = get_logger(__name__)


def parse_wkt_multipolygon_manual(wkt_string: str) -> Optional[List[List[List[List[float]]]]]:
    """WKT MULTIPOLYGON 문자열을 수동으로 파싱
    
    Args:
        wkt_string: WKT 형식의 MULTIPOLYGON 문자열
        예: "MULTIPOLYGON((x1 y1, x2 y2, ...))"
        
    Returns:
        GeoJSON MultiPolygon coordinates 형식 또는 None
    """
    if not wkt_string or not isinstance(wkt_string, str):
        return None
    
    wkt_string = wkt_string.strip()
    
    # MULTIPOLYGON 키워드 제거
    if wkt_string.upper().startswith('MULTIPOLYGON'):
        # MULTIPOLYGON((...)) 형식에서 좌표 부분만 추출
        match_start = wkt_string.find('(')
        if match_start == -1:
            return None
        coords_str = wkt_string[match_start:]
    else:
        coords_str = wkt_string
    
    # 정규식이나 간단한 파싱으로 처리
    # MULTIPOLYGON((x1 y1, x2 y2, ...)) 형식
    polygons = []
    
    try:
        # 가장 바깥쪽 괄호 제거
        if coords_str.startswith('(') and coords_str.endswith(')'):
            coords_str = coords_str[1:-1]
        
        # 각 polygon 파싱 (괄호로 구분)
        polygon_strs = []
        depth = 0
        start = 0
        
        for i, char in enumerate(coords_str):
            if char == '(':
                if depth == 0:
                    start = i
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    polygon_strs.append(coords_str[start:i+1])
        
        # 각 polygon 처리
        for polygon_str in polygon_strs:
            # 괄호 제거
            if polygon_str.startswith('(') and polygon_str.endswith(')'):
                polygon_str = polygon_str[1:-1]
            
            # ring 파싱 (첫 번째 ring만 사용, 내부 ring은 무시)
            rings = []
            ring_start = 0
            depth = 0
            
            for i, char in enumerate(polygon_str):
                if char == '(':
                    if depth == 0:
                        ring_start = i
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        ring_str = polygon_str[ring_start+1:i]
                        # 좌표 파싱
                        ring_coords = []
                        for coord_pair in ring_str.split(','):
                            coord_pair = coord_pair.strip()
                            if not coord_pair:
                                continue
                            parts = coord_pair.split()
                            if len(parts) >= 2:
                                try:
                                    x = float(parts[0])
                                    y = float(parts[1])
                                    ring_coords.append([x, y])
                                except ValueError:
                                    continue
                        if ring_coords:
                            rings.append(ring_coords)
            
            if rings:
                polygons.append(rings)
        
        if polygons:
            return polygons
    except Exception as e:
        logger.debug(f"WKT 수동 파싱 실패: {e}")
        return None
    
    return None


def fix_wkt_format(wkt_string: str) -> str:
    """WKT 형식을 표준 형식으로 수정
    
    VWorld CSV의 WKT는 MULTIPOLYGON((...)) 형식인데,
    표준은 MULTIPOLYGON(((...))) 형식입니다.
    단일 polygon인 경우 POLYGON으로 변환하거나 올바른 형식으로 수정합니다.
    """
    wkt_string = wkt_string.strip()
    
    # MULTIPOLYGON((...)) -> MULTIPOLYGON(((...))) 형식으로 수정
    if wkt_string.upper().startswith('MULTIPOLYGON'):
        # MULTIPOLYGON((...)) 형식인지 확인
        if wkt_string.count('(') == 2 and wkt_string.count(')') == 2:
            # 단일 polygon이므로 POLYGON으로 변환
            wkt_string = wkt_string.replace('MULTIPOLYGON', 'POLYGON', 1)
        elif wkt_string.count('(') == 2:
            # MULTIPOLYGON((...)) -> MULTIPOLYGON(((...))) 형식으로 수정
            # 첫 번째 ( 다음에 ( 추가
            first_paren = wkt_string.find('(')
            if first_paren != -1:
                wkt_string = wkt_string[:first_paren+1] + '(' + wkt_string[first_paren+1:]
                # 마지막 ) 앞에 ) 추가
                last_paren = wkt_string.rfind(')')
                if last_paren != -1:
                    wkt_string = wkt_string[:last_paren] + ')' + wkt_string[last_paren:]
    
    return wkt_string


def parse_wkt_to_geojson_geometry(wkt_string: str) -> Optional[Dict[str, Any]]:
    """WKT 문자열을 GeoJSON geometry로 변환
    
    Args:
        wkt_string: WKT 형식 문자열
        
    Returns:
        GeoJSON geometry 객체 또는 None
    """
    if not wkt_string or not isinstance(wkt_string, str):
        return None
    
    wkt_string = wkt_string.strip()
    
    # 큰따옴표 제거 (CSV에서 온 경우)
    if wkt_string.startswith('"') and wkt_string.endswith('"'):
        wkt_string = wkt_string[1:-1]
    
    # WKT 형식 수정 (VWorld 특수 형식 처리)
    wkt_string = fix_wkt_format(wkt_string)
    
    # shapely 사용 (가능한 경우) - 가장 안정적
    if HAS_SHAPELY:
        try:
            geom = wkt.loads(wkt_string)
            geojson_geom = mapping(geom)
            # shapely의 mapping은 GeoJSON 형식과 호환됨
            return geojson_geom
        except Exception as e:
            logger.debug(f"shapely 파싱 실패 ({wkt_string[:50]}...): {e}")
            # shapely 실패 시 수동 파싱 시도
    
    # 수동 파싱 (MULTIPOLYGON만 지원)
    if wkt_string.upper().startswith('MULTIPOLYGON'):
        coords = parse_wkt_multipolygon_manual(wkt_string)
        if coords:
            return {
                'type': 'MultiPolygon',
                'coordinates': coords
            }
    elif wkt_string.upper().startswith('POLYGON'):
        # POLYGON 수동 파싱
        try:
            match_start = wkt_string.find('(')
            match_end = wkt_string.rfind(')')
            if match_start != -1 and match_end != -1:
                coords_str = wkt_string[match_start + 1:match_end]
                # 첫 번째 ring만 파싱
                ring_coords = []
                for coord_pair in coords_str.split(','):
                    coord_pair = coord_pair.strip()
                    if not coord_pair:
                        continue
                    parts = coord_pair.split()
                    if len(parts) >= 2:
                        try:
                            x = float(parts[0])
                            y = float(parts[1])
                            ring_coords.append([x, y])
                        except ValueError:
                            continue
                if ring_coords:
                    return {
                        'type': 'Polygon',
                        'coordinates': [ring_coords]
                    }
        except Exception as e:
            logger.debug(f"POLYGON 파싱 실패: {e}")
        return None
    elif wkt_string.upper().startswith('POINT'):
        # POINT 처리
        try:
            match_start = wkt_string.find('(')
            match_end = wkt_string.rfind(')')
            if match_start != -1 and match_end != -1:
                coords_str = wkt_string[match_start + 1:match_end]
                parts = coords_str.split()
                if len(parts) >= 2:
                    return {
                        'type': 'Point',
                        'coordinates': [float(parts[0]), float(parts[1])]
                    }
        except Exception as e:
            logger.warning(f"POINT 파싱 실패: {e}")
        return None
    
    return None


def transform_coordinates_3857_to_4326(coords: Any, transformer: Optional[Transformer]) -> Any:
    """EPSG:3857 좌표를 EPSG:4326으로 변환
    
    Args:
        coords: GeoJSON coordinates (다양한 형식 지원)
        transformer: pyproj Transformer 객체
        
    Returns:
        변환된 coordinates
    """
    if transformer is None:
        return coords
    
    def transform_point(point: List[float]) -> List[float]:
        """단일 점 변환"""
        if len(point) < 2:
            return point
        try:
            lon, lat = transformer.transform(point[0], point[1])
            return [lon, lat]
        except Exception as e:
            logger.debug(f"좌표 변환 실패 ({point[0]}, {point[1]}): {e}")
            return point
    
    def transform_ring(ring: List[List[float]]) -> List[List[float]]:
        """링 변환"""
        return [transform_point(point) for point in ring]
    
    def transform_polygon(polygon: List[List[List[float]]]) -> List[List[List[float]]]:
        """폴리곤 변환"""
        return [transform_ring(ring) for ring in polygon]
    
    def transform_multipolygon(multipolygon: List[List[List[List[float]]]]) -> List[List[List[List[float]]]]:
        """멀티폴리곤 변환"""
        return [transform_polygon(polygon) for polygon in multipolygon]
    
    # 좌표 형식에 따라 변환
    if isinstance(coords, list):
        if len(coords) > 0:
            # 첫 번째 요소로 타입 판단
            first = coords[0]
            if isinstance(first, (int, float)):
                # Point
                return transform_point(coords)
            elif isinstance(first, list) and len(first) > 0:
                if isinstance(first[0], (int, float)):
                    # LineString 또는 Polygon ring
                    return transform_ring(coords)
                elif isinstance(first[0], list) and len(first[0]) > 0:
                    if isinstance(first[0][0], (int, float)):
                        # Polygon
                        return transform_polygon(coords)
                    elif isinstance(first[0][0], list):
                        # MultiPolygon
                        return transform_multipolygon(coords)
    
    return coords


def convert_csv_to_geojson(
    csv_path: Path,
    output_path: Optional[Path] = None,
    convert_coords: bool = True
) -> Path:
    """CSV 파일을 GeoJSON으로 변환
    
    Args:
        csv_path: 입력 CSV 파일 경로
        output_path: 출력 GeoJSON 파일 경로 (None이면 자동 생성)
        convert_coords: 좌표 변환 여부 (EPSG:3857 → EPSG:4326)
        
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
            transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
            logger.info("좌표 변환기 초기화 완료 (EPSG:3857 → EPSG:4326)")
        except Exception as e:
            logger.warning(f"좌표 변환기 초기화 실패: {e}. 좌표 변환 없이 진행합니다.")
            transformer = None
    elif convert_coords and not HAS_PYPROJ:
        logger.warning("pyproj가 설치되지 않아 좌표 변환 없이 진행합니다.")
        logger.warning("EPSG:3857 좌표를 그대로 사용합니다. (GeoJSON 표준은 WGS84입니다)")
    
    # 출력 파일 경로 생성
    if output_path is None:
        output_dir = csv_path.parent
        output_filename = csv_path.stem + '.geojson'
        output_path = output_dir / output_filename
    else:
        output_path = Path(output_path)
        if output_path.suffix == '' or output_path.suffix == '.json':
            output_path = output_path.with_suffix('.geojson')
    
    # CSV 읽기 및 변환
    logger.info(f"CSV 파일 읽기: {csv_path}")
    features = []
    skipped_count = 0
    
    BOM = '\uFEFF'  # UTF-8 BOM – CSV 헤더에 붙으면 첫 컬럼명이 "﻿bld_mnnm" 등으로 깨짐

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # 헤더 제외, 2부터 시작
            wkt = (row.get('wkt', '') or row.get(BOM + 'wkt', '')).strip()
            if not wkt:
                skipped_count += 1
                continue
            
            # WKT를 GeoJSON geometry로 변환
            geometry = parse_wkt_to_geojson_geometry(wkt)
            if not geometry:
                skipped_count += 1
                if skipped_count <= 5:  # 처음 5개만 상세 로그
                    logger.warning(f"행 {row_num} WKT 파싱 실패: {wkt[:100]}...")
                continue
            
            # 좌표 변환
            if transformer and 'coordinates' in geometry and 'type' in geometry:
                geom_type = geometry['type']
                coords = geometry['coordinates']
                
                def transform_point(pt):
                    """단일 점 변환"""
                    try:
                        lon, lat = transformer.transform(pt[0], pt[1])
                        return [lon, lat]
                    except:
                        return pt
                
                if geom_type == 'Point':
                    geometry['coordinates'] = transform_point(coords)
                elif geom_type == 'LineString':
                    geometry['coordinates'] = [transform_point(pt) for pt in coords]
                elif geom_type == 'Polygon':
                    # Polygon: [[[x, y], ...], ...]
                    geometry['coordinates'] = [
                        [transform_point(pt) for pt in ring]
                        for ring in coords
                    ]
                elif geom_type == 'MultiPolygon':
                    # MultiPolygon: [[[[x, y], ...], ...], ...]
                    geometry['coordinates'] = [
                        [
                            [transform_point(pt) for pt in ring]
                            for ring in polygon
                        ]
                        for polygon in coords
                    ]
            
            # properties 생성 (wkt 제외, 키에서 BOM 제거)
            properties = {}
            for k, v in row.items():
                key = k.lstrip(BOM) if isinstance(k, str) else k
                if key == 'wkt':
                    continue
                properties[key] = v
            
            # GeoJSON Feature 생성
            feature = {
                'type': 'Feature',
                'geometry': geometry,
                'properties': properties
            }
            features.append(feature)
    
    logger.info(f"변환 완료: {len(features)}개 Feature 생성, {skipped_count}개 건너뜀")
    
    # GeoJSON 생성
    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'source': str(csv_path.name),
            'conversion_time': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'total_features': len(features),
            'coordinate_system': 'WGS84' if transformer else 'EPSG:3857',
            'skipped_count': skipped_count,
            'source_crs': 'EPSG:3857',
            'target_crs': 'EPSG:4326' if transformer else 'EPSG:3857'
        }
    }
    
    # 파일 저장
    logger.info(f"GeoJSON 파일 저장: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 변환 완료: {output_path}")
    logger.info(f"   - 총 {len(features)}개 Feature")
    logger.info(f"   - 좌표계: {geojson['metadata']['coordinate_system']}")
    
    return output_path


def convert_directory_csvs_to_geojson(
    directory: Path,
    pattern: str = "*.csv",
    convert_coords: bool = True
) -> List[Path]:
    """디렉토리 내 모든 CSV 파일을 GeoJSON으로 변환
    
    Args:
        directory: CSV 파일이 있는 디렉토리
        pattern: 파일 패턴 (기본값: "*.csv")
        convert_coords: 좌표 변환 여부
        
    Returns:
        생성된 GeoJSON 파일 경로 리스트
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"디렉토리를 찾을 수 없습니다: {directory}")
    
    csv_files = list(directory.glob(pattern))
    if not csv_files:
        logger.warning(f"CSV 파일을 찾을 수 없습니다: {directory}/{pattern}")
        return []
    
    logger.info(f"{len(csv_files)}개 CSV 파일 발견")
    
    geojson_files = []
    for csv_file in csv_files:
        try:
            geojson_file = convert_csv_to_geojson(csv_file, convert_coords=convert_coords)
            geojson_files.append(geojson_file)
        except Exception as e:
            logger.error(f"변환 실패 ({csv_file.name}): {e}")
    
    return geojson_files


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='VWorld CSV 파일을 GeoJSON으로 변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 단일 파일 변환
  python convert_csv_to_geojson.py data.csv
  
  # 디렉토리 내 모든 CSV 변환
  python convert_csv_to_geojson.py --directory data/raw/vworld/vworld_seongsu_20260127_104656
  
  # 좌표 변환 없이 변환 (EPSG:3857 유지)
  python convert_csv_to_geojson.py data.csv --no-convert-coords
        """
    )
    
    parser.add_argument(
        'input',
        nargs='?',
        help='입력 CSV 파일 경로 또는 디렉토리'
    )
    
    parser.add_argument(
        '--directory', '-d',
        help='디렉토리 내 모든 CSV 파일 변환'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='출력 GeoJSON 파일 경로 (단일 파일 변환 시)'
    )
    
    parser.add_argument(
        '--no-convert-coords',
        action='store_true',
        help='좌표 변환 없이 변환 (EPSG:3857 유지)'
    )
    
    parser.add_argument(
        '--pattern',
        default='*.csv',
        help='CSV 파일 패턴 (기본값: *.csv)'
    )
    
    args = parser.parse_args()
    
    if args.directory:
        # 디렉토리 모드
        directory = Path(args.directory)
        geojson_files = convert_directory_csvs_to_geojson(
            directory,
            pattern=args.pattern,
            convert_coords=not args.no_convert_coords
        )
        logger.info(f"총 {len(geojson_files)}개 GeoJSON 파일 생성 완료")
    elif args.input:
        # 단일 파일 모드
        csv_path = Path(args.input)
        output_path = Path(args.output) if args.output else None
        geojson_file = convert_csv_to_geojson(
            csv_path,
            output_path=output_path,
            convert_coords=not args.no_convert_coords
        )
        logger.info(f"GeoJSON 파일 생성: {geojson_file}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
