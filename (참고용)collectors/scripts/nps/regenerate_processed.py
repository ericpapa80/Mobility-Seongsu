# -*- coding: utf-8 -*-
"""완료된 원본 CSV 파일로부터 processed 데이터 재생성"""

import sys
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.scraper import NPSScraper
from plugins.nps.normalizer import NPSNormalizer
from core.storage.file_storage import FileStorage
from core.logger import get_logger

logger = get_logger(__name__)


def regenerate_processed(csv_path: str):
    """완료된 CSV 파일로부터 processed 데이터 재생성
    
    Args:
        csv_path: 완료된 원본 CSV 파일 경로
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return
    
    print("=" * 80)
    print("Processed 데이터 재생성")
    print("=" * 80)
    print(f"입력 파일: {csv_path}")
    
    # CSV 파일 읽기
    print("\nCSV 파일 로딩 중...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"전체 레코드: {len(df):,}개")
    
    # 좌표 확인
    coords_count = len(df[df['x'].notna() & df['y'].notna()])
    print(f"좌표 있는 레코드: {coords_count:,}개 ({coords_count/len(df)*100:.1f}%)")
    
    # 데이터 변환
    print("\n데이터 정규화 중...")
    records = df.to_dict('records')
    data = {
        'total_count': len(records),
        'records': records
    }
    
    # Normalizer와 Storage 초기화
    normalizer = NPSNormalizer()
    storage = FileStorage(
        base_dir=project_root / "data" / "processed",
        config={'source_name': 'nps', 'save_json': True, 'save_csv': True}
    )
    
    # 메타데이터 준비
    metadata = {
        'csv_source': str(csv_path),
        'filter_address': '성수동1가/2가',
        'filter_active_only': True,
        'total_count': len(df),
        'geocoding_completed': True
    }
    
    # 정규화 및 저장
    normalized_data = normalizer.normalize(data, metadata)
    processed_path = storage.save(normalized_data, metadata)
    
    print("\n" + "=" * 80)
    print("재생성 완료")
    print("=" * 80)
    print(f"Processed 데이터 저장 위치: {processed_path}")
    print("✅ 완료!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='완료된 CSV 파일로부터 processed 데이터 재생성')
    parser.add_argument('csv_path', help='완료된 원본 CSV 파일 경로')
    
    args = parser.parse_args()
    regenerate_processed(args.csv_path)

