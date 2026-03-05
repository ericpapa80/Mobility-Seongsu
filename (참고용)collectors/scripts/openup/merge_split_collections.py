"""분할 수집된 파일들을 통합하는 스크립트."""

import sys
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.file_handler import FileHandler


def find_split_files(session_dir: Path, file_type: str) -> List[Path]:
    """세션 디렉토리에서 분할 파일들을 찾습니다.
    
    Args:
        session_dir: 세션 디렉토리 경로
        file_type: 'buildings' 또는 'stores'
    
    Returns:
        분할 파일 경로 리스트 (정렬됨)
    """
    pattern = f"openup_seoul_gyeonggi_{file_type}_*_split*.json"
    split_files = sorted(session_dir.glob(pattern))
    return split_files


def merge_buildings(session_dir: Path) -> Dict[str, Any]:
    """건물 데이터를 통합합니다."""
    split_files = find_split_files(session_dir, "buildings")
    
    if not split_files:
        print(f"⚠️ 건물 분할 파일을 찾을 수 없습니다: {session_dir}")
        return None
    
    print(f"\n건물 데이터 통합 시작: {len(split_files)}개 분할 파일")
    
    all_buildings = []
    seen_building_hashes = set()
    total_buildings = 0
    
    for split_file in split_files:
        print(f"  처리 중: {split_file.name}")
        with open(split_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        buildings = data.get('data', [])
        for building in buildings:
            building_hash = building.get('building_hash')
            if building_hash and building_hash not in seen_building_hashes:
                seen_building_hashes.add(building_hash)
                all_buildings.append(building)
                total_buildings += 1
    
    print(f"  ✓ 통합 완료: {total_buildings}개 건물 (중복 제거됨)")
    
    return {
        "data": all_buildings,
        "metadata": {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "total_buildings": total_buildings,
            "split_files_count": len(split_files),
            "collection_method": "hash_to_sales_merged",
            "merged_from": [f.name for f in split_files]
        }
    }


def merge_stores(session_dir: Path) -> Dict[str, Any]:
    """매장 데이터를 통합합니다."""
    split_files = find_split_files(session_dir, "stores")
    
    if not split_files:
        print(f"⚠️ 매장 분할 파일을 찾을 수 없습니다: {session_dir}")
        return None
    
    print(f"\n매장 데이터 통합 시작: {len(split_files)}개 분할 파일")
    
    all_stores = []
    seen_store_ids = set()
    total_stores = 0
    total_buildings = 0
    total_store_ids = 0
    
    for split_file in split_files:
        print(f"  처리 중: {split_file.name}")
        with open(split_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        stores = data.get('data', [])
        metadata = data.get('metadata', {})
        total_buildings = max(total_buildings, metadata.get('total_buildings', 0))
        total_store_ids = max(total_store_ids, metadata.get('total_store_ids', 0))
        
        for store in stores:
            store_id = store.get('storeId')
            if store_id and store_id not in seen_store_ids:
                seen_store_ids.add(store_id)
                all_stores.append(store)
                total_stores += 1
    
    print(f"  ✓ 통합 완료: {total_stores}개 매장 (중복 제거됨)")
    
    return {
        "data": all_stores,
        "metadata": {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "total_stores": total_stores,
            "total_buildings": total_buildings,
            "total_store_ids": total_store_ids,
            "split_files_count": len(split_files),
            "collection_method": "hash_to_sales_merged",
            "merged_from": [f.name for f in split_files]
        }
    }


def main():
    """메인 실행 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='분할 수집 파일 통합')
    parser.add_argument('--session-dir', type=str, help='세션 디렉토리 경로 (예: split_session_20260113_132926)')
    parser.add_argument('--auto', action='store_true', help='가장 최근 세션 디렉토리 자동 선택')
    args = parser.parse_args()
    
    openup_dir = project_root / "data" / "raw" / "openup"
    
    # 세션 디렉토리 찾기
    if args.session_dir:
        session_dir = openup_dir / args.session_dir
    elif args.auto:
        # 가장 최근 세션 디렉토리 찾기
        session_dirs = [d for d in openup_dir.iterdir() if d.is_dir() and d.name.startswith('split_session_')]
        if not session_dirs:
            print("⚠️ 세션 디렉토리를 찾을 수 없습니다.")
            return
        session_dir = max(session_dirs, key=lambda p: p.stat().st_mtime)
        print(f"자동 선택된 세션: {session_dir.name}")
    else:
        # 사용 가능한 세션 디렉토리 목록 표시
        session_dirs = [d for d in openup_dir.iterdir() if d.is_dir() and d.name.startswith('split_session_')]
        if not session_dirs:
            print("⚠️ 세션 디렉토리를 찾을 수 없습니다.")
            return
        
        print("사용 가능한 세션 디렉토리:")
        for i, sd in enumerate(sorted(session_dirs, key=lambda p: p.stat().st_mtime, reverse=True), 1):
            print(f"  {i}. {sd.name}")
        
        choice = input("\n세션 번호를 선택하세요 (또는 Enter로 가장 최근 것 선택): ").strip()
        if choice.isdigit():
            session_dir = sorted(session_dirs, key=lambda p: p.stat().st_mtime, reverse=True)[int(choice) - 1]
        else:
            session_dir = max(session_dirs, key=lambda p: p.stat().st_mtime)
    
    if not session_dir.exists():
        print(f"⚠️ 세션 디렉토리가 존재하지 않습니다: {session_dir}")
        return
    
    print(f"\n{'='*80}")
    print(f"분할 수집 파일 통합")
    print(f"세션 디렉토리: {session_dir.name}")
    print(f"{'='*80}")
    
    # 건물 데이터 통합
    buildings_data = merge_buildings(session_dir)
    if buildings_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        buildings_json_file = session_dir / f"openup_seoul_gyeonggi_buildings_merged_{timestamp}.json"
        with open(buildings_json_file, 'w', encoding='utf-8') as f:
            json.dump(buildings_data, f, ensure_ascii=False, indent=2)
        print(f"✓ 건물 통합 JSON 저장: {buildings_json_file.name}")
        
        # CSV 저장
        buildings_csv_file = session_dir / f"openup_seoul_gyeonggi_buildings_merged_{timestamp}.csv"
        FileHandler.save_csv(buildings_data['data'], buildings_csv_file)
        print(f"✓ 건물 통합 CSV 저장: {buildings_csv_file.name}")
    
    # 매장 데이터 통합
    stores_data = merge_stores(session_dir)
    if stores_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stores_json_file = session_dir / f"openup_seoul_gyeonggi_stores_merged_{timestamp}.json"
        with open(stores_json_file, 'w', encoding='utf-8') as f:
            json.dump(stores_data, f, ensure_ascii=False, indent=2)
        print(f"✓ 매장 통합 JSON 저장: {stores_json_file.name}")
        
        # CSV 저장
        stores_csv_file = session_dir / f"openup_seoul_gyeonggi_stores_merged_{timestamp}.csv"
        # CSV 변환을 위한 데이터 준비
        stores_for_csv = []
        for store in stores_data['data']:
            store_copy = store.copy()
            # 중첩된 구조를 평탄화
            if 'sales' in store_copy:
                sales = store_copy.pop('sales', {})
                for key, value in sales.items():
                    store_copy[f'sales_{key}'] = value
            stores_for_csv.append(store_copy)
        FileHandler.save_csv(stores_for_csv, stores_csv_file)
        print(f"✓ 매장 통합 CSV 저장: {stores_csv_file.name}")
    
    print(f"\n{'='*80}")
    print("통합 완료!")
    if buildings_data:
        print(f"  건물: {buildings_data['metadata']['total_buildings']}개")
    if stores_data:
        print(f"  매장: {stores_data['metadata']['total_stores']}개")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
