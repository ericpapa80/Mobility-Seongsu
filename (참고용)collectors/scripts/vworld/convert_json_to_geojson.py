"""VWorld API 응답 JSON을 EPSG:4326 GeoJSON으로 변환하는 스크립트

API 수집으로 생성된 JSON(features 배열 포함)을 읽어
좌표계만 EPSG:3857 → EPSG:4326으로 변환하여 표준 GeoJSON으로 저장합니다.
CSV보다 단순: WKT 파싱 없이 geometry.coordinates만 변환합니다.
"""

import json
import sys
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import get_logger

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

logger = get_logger(__name__)


def _transform_point(transformer: Any, pt: List[float]) -> List[float]:
    if len(pt) < 2:
        return pt
    try:
        lon, lat = transformer.transform(pt[0], pt[1])
        return [lon, lat]
    except Exception:
        return pt


def transform_geometry_coordinates(geometry: dict, transformer: Any) -> None:
    """geometry.coordinates를 제자리에서 EPSG:3857 → EPSG:4326으로 변환."""
    if not geometry or not transformer or 'coordinates' not in geometry:
        return
    geom_type = geometry.get('type', '')
    coords = geometry['coordinates']

    if geom_type == 'Point':
        geometry['coordinates'] = _transform_point(transformer, coords)
    elif geom_type == 'LineString':
        geometry['coordinates'] = [_transform_point(transformer, pt) for pt in coords]
    elif geom_type == 'Polygon':
        geometry['coordinates'] = [
            [_transform_point(transformer, pt) for pt in ring]
            for ring in coords
        ]
    elif geom_type == 'MultiPolygon':
        geometry['coordinates'] = [
            [
                [_transform_point(transformer, pt) for pt in ring]
                for ring in polygon
            ]
            for polygon in coords
        ]


def convert_json_to_geojson(
    json_path: Path,
    output_path: Optional[Path] = None,
    convert_coords: bool = True,
) -> Path:
    """
    VWorld API JSON 파일을 EPSG:4326 GeoJSON으로 변환합니다.

    Args:
        json_path: 입력 JSON 경로 (features 배열이 있는 API 응답 형식)
        output_path: 출력 GeoJSON 경로. None이면 같은 디렉토리에 stem.geojson
        convert_coords: True면 3857→4326 변환, False면 좌표 그대로

    Returns:
        저장된 GeoJSON 파일 경로
    """
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")

    if output_path is None:
        output_path = json_path.parent / (json_path.stem + '.geojson')
    else:
        output_path = Path(output_path)
        if output_path.suffix not in ('.geojson', '.json'):
            output_path = output_path.with_suffix('.geojson')

    transformer = None
    if convert_coords and HAS_PYPROJ:
        try:
            transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
            logger.info("좌표 변환기 초기화 (EPSG:3857 → EPSG:4326)")
        except Exception as e:
            logger.warning(f"좌표 변환 초기화 실패: {e}. 좌표 변환 없이 진행합니다.")
    elif convert_coords and not HAS_PYPROJ:
        logger.warning("pyproj 없음. 좌표 변환 없이 진행합니다.")

    logger.info(f"JSON 읽기: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    features = data.get('features', [])
    if not features:
        logger.warning("'features' 배열이 비어 있거나 없습니다.")
        features = []

    for feat in features:
        if isinstance(feat, dict) and feat.get('geometry'):
            transform_geometry_coordinates(feat['geometry'], transformer)

    fc = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'source': json_path.name,
            'conversion_time': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'total_features': len(features),
            'coordinate_system': 'WGS84' if transformer else 'EPSG:3857',
            'source_crs': 'EPSG:3857',
            'target_crs': 'EPSG:4326' if transformer else 'EPSG:3857',
        },
    }
    if 'layer_id' in data:
        fc['metadata']['layer_id'] = data['layer_id']
    if 'region' in data:
        fc['metadata']['region'] = data['region']
    if 'collection_timestamp' in data:
        fc['metadata']['collection_timestamp'] = data['collection_timestamp']

    logger.info(f"GeoJSON 저장: {output_path} ({len(features)} features)")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 변환 완료: {output_path} (좌표계: {fc['metadata']['coordinate_system']})")
    return output_path


def convert_directory_jsons_to_geojson(
    directory: Path,
    pattern: str = "*.json",
    exclude_summary: bool = True,
    convert_coords: bool = True,
) -> List[Path]:
    """
    디렉토리 내 VWorld API JSON 파일들을 GeoJSON으로 일괄 변환합니다.

    Args:
        directory: 대상 디렉토리
        pattern: 파일 패턴 (기본 *.json)
        exclude_summary: True면 *summary*.json, *collection_summary* 제외
        convert_coords: 3857→4326 변환 여부

    Returns:
        생성된 GeoJSON 파일 경로 목록
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"디렉토리를 찾을 수 없습니다: {directory}")

    candidates = list(directory.glob(pattern))
    if exclude_summary:
        candidates = [
            p for p in candidates
            if 'summary' not in p.name.lower() and not p.name.endswith('.geojson')
        ]
    if not candidates:
        logger.warning(f"대상 JSON이 없습니다: {directory}/{pattern}")
        return []

    logger.info(f"대상 JSON {len(candidates)}개")
    result = []
    for p in candidates:
        try:
            out = convert_json_to_geojson(p, output_path=None, convert_coords=convert_coords)
            result.append(out)
        except Exception as e:
            logger.error(f"변환 실패 ({p.name}): {e}")
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='VWorld API JSON을 EPSG:4326 GeoJSON으로 변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예:
  # 단일 파일
  python convert_json_to_geojson.py seongsu_lt-c-landinfobasemap_20260127_105315.json

  # 디렉토리 내 모든 레이어 JSON 변환 (summary 제외)
  python convert_json_to_geojson.py -d data/raw/vworld/vworld_seongsu_20260127_104656

  # 좌표 변환 없이 복사
  python convert_json_to_geojson.py file.json --no-convert-coords
"""
    )
    parser.add_argument('input', nargs='?', help='입력 JSON 파일')
    parser.add_argument('-d', '--directory', help='디렉토리 내 JSON 일괄 변환')
    parser.add_argument('-o', '--output', help='출력 GeoJSON 경로 (단일 파일 시)')
    parser.add_argument('--no-convert-coords', action='store_true', help='좌표 변환 하지 않음')
    parser.add_argument('--pattern', default='*.json', help='디렉토리 모드 시 파일 패턴')
    parser.add_argument('--no-exclude-summary', action='store_true', help='summary JSON 포함')

    args = parser.parse_args()

    if args.directory:
        convert_directory_jsons_to_geojson(
            Path(args.directory),
            pattern=args.pattern,
            exclude_summary=not args.no_exclude_summary,
            convert_coords=not args.no_convert_coords,
        )
        return

    if args.input:
        convert_json_to_geojson(
            Path(args.input),
            output_path=Path(args.output) if args.output else None,
            convert_coords=not args.no_convert_coords,
        )
        return

    parser.print_help()


if __name__ == '__main__':
    main()
