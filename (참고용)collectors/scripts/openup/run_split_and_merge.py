"""토큰 파일을 10등분하여 분할 실행하고 최종 병합하는 스크립트.

사용 방법:
    python collectors/scripts/openup/run_split_and_merge.py --token-file 260118_token
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import argparse
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger

logger = get_logger(__name__)


def load_tokens_from_file(token_filename: str) -> tuple[str, list[str]]:
    """토큰 파일에서 access-token과 cell_tokens를 로드."""
    import re
    
    token_file = project_root / "docs" / "sources" / "openup" / "raw" / token_filename
    if not token_file.exists():
        raise FileNotFoundError(f"토큰 파일을 찾을 수 없습니다: {token_file}")
    
    content = token_file.read_text(encoding='utf-8')
    
    # access-token 추출
    access_token_match = re.search(r'OPENUP_ACCESS_TOKEN\s*=\s*([a-f0-9-]+)', content)
    access_token = access_token_match.group(1) if access_token_match else None
    
    if not access_token:
        raise ValueError("access-token을 찾을 수 없습니다.")
    
    # cell_tokens 추출 (중복 제거)
    tokens = re.findall(r'"([^"]+)"', content)
    unique_tokens = sorted(list(set(tokens)))
    
    return access_token, unique_tokens


def split_tokens(tokens: list[str], split_count: int = 10) -> list[list[str]]:
    """토큰 리스트를 지정된 개수로 분할."""
    total_tokens = len(tokens)
    tokens_per_split = total_tokens // split_count
    splits = []
    
    for i in range(split_count):
        start_idx = i * tokens_per_split
        if i == split_count - 1:
            # 마지막 분할은 나머지 모두 포함
            end_idx = total_tokens
        else:
            end_idx = start_idx + tokens_per_split
        splits.append(tokens[start_idx:end_idx])
    
    return splits


def merge_json_files(json_files: List[Path], output_file: Path, data_key: str = "data") -> None:
    """여러 JSON 파일을 하나로 병합."""
    merged_data = []
    merged_metadata = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "collection_method": "hash_to_sales",
        "merged_from": [str(f.name) for f in json_files],
        "split_count": len(json_files)
    }
    
    total_items = 0
    for json_file in json_files:
        if not json_file.exists():
            logger.warning(f"⚠️ 파일을 찾을 수 없습니다: {json_file}")
            continue
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data_key in data:
                items = data[data_key]
                merged_data.extend(items)
                total_items += len(items)
                
                # 메타데이터 통합
                if "metadata" in data:
                    metadata = data["metadata"]
                    merged_metadata.setdefault("split_details", []).append({
                        "file": json_file.name,
                        "items": len(items),
                        "split_index": metadata.get("split_index"),
                        "timestamp": metadata.get("timestamp")
                    })
        
        except Exception as e:
            logger.error(f"❌ 파일 읽기 오류 ({json_file}): {e}")
            continue
    
    merged_metadata["total_items"] = total_items
    
    # 병합된 데이터 저장
    output_data = {
        "data": merged_data,
        "metadata": merged_metadata
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ 병합 완료: {output_file} ({total_items}개 항목)")


def merge_csv_files(csv_files: List[Path], output_file: Path) -> None:
    """여러 CSV 파일을 하나로 병합."""
    import csv
    
    if not csv_files:
        return
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    first_file = True
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
        writer = None
        
        for csv_file in csv_files:
            if not csv_file.exists():
                logger.warning(f"⚠️ 파일을 찾을 수 없습니다: {csv_file}")
                continue
            
            try:
                with open(csv_file, 'r', encoding='utf-8-sig', newline='') as infile:
                    reader = csv.DictReader(infile)
                    
                    if first_file:
                        # 첫 번째 파일에서 헤더 읽기
                        fieldnames = reader.fieldnames
                        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                        writer.writeheader()
                        first_file = False
                    
                    # 데이터 복사
                    for row in reader:
                        writer.writerow(row)
            
            except Exception as e:
                logger.error(f"❌ CSV 파일 읽기 오류 ({csv_file}): {e}")
                continue
    
    if writer:
        logger.info(f"✓ CSV 병합 완료: {output_file}")


def main():
    """메인 실행 함수."""
    parser = argparse.ArgumentParser(
        description='토큰 파일을 10등분하여 분할 실행하고 최종 병합'
    )
    parser.add_argument(
        '--token-file',
        type=str,
        default='260118_token',
        help='토큰 파일명 (기본값: 260118_token)'
    )
    parser.add_argument(
        '--split-count',
        type=int,
        default=10,
        help='분할 개수 (기본값: 10)'
    )
    parser.add_argument(
        '--start-from',
        type=int,
        default=1,
        help='시작할 분할 번호 (기본값: 1)'
    )
    parser.add_argument(
        '--end-at',
        type=int,
        default=None,
        help='종료할 분할 번호 (기본값: 전체)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='출력 디렉토리명 (기본값: 자동 생성)'
    )
    parser.add_argument(
        '--skip-execution',
        action='store_true',
        help='실행 건너뛰고 병합만 수행'
    )
    
    args = parser.parse_args()
    
    # 토큰 파일 로드
    logger.info(f"📂 토큰 파일 로드: {args.token_file}")
    access_token, all_tokens = load_tokens_from_file(args.token_file)
    logger.info(f"  ✓ Access-token: {access_token[:20]}...")
    logger.info(f"  ✓ Cell-tokens: {len(all_tokens)}개")
    
    # 토큰 분할
    splits = split_tokens(all_tokens, args.split_count)
    logger.info(f"\n📦 {args.split_count}등분 결과:")
    for i, split in enumerate(splits, 1):
        logger.info(f"  분할 {i}: {len(split)}개")
    
    # 출력 디렉토리 설정
    if args.output_dir:
        output_dir_name = args.output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir_name = f"split_session_{timestamp}"
    
    output_dir = project_root / "data" / "raw" / "openup" / output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"\n📁 출력 디렉토리: {output_dir}")
    
    # 환경 변수로 세션 타임스탬프 설정 (스크립트에서 사용할 수 있도록)
    session_timestamp = output_dir.name.replace("split_session_", "")
    os.environ['SPLIT_SESSION_TIMESTAMP'] = session_timestamp
    
    # 분할 실행
    if not args.skip_execution:
        start_idx = args.start_from - 1
        end_idx = args.end_at if args.end_at else args.split_count
        
        logger.info(f"\n🚀 분할 실행 시작: {args.start_from} ~ {end_idx}")
        
        for split_index in range(start_idx, end_idx):
            split_num = split_index + 1
            logger.info(f"\n{'='*80}")
            logger.info(f"분할 {split_num}/{args.split_count} 실행 중...")
            logger.info(f"{'='*80}")
            
            # 환경 변수로 split_index 설정
            env = os.environ.copy()
            env['SPLIT_INDEX'] = str(split_num)
            env['OPENUP_SPLIT_OUTPUT_DIR'] = str(output_dir)
            
            # 스크립트 실행 (현재 스크립트와 같은 디렉토리에 있음)
            script_path = Path(__file__).parent / "collect_seongsu_hash_to_sales.py"
            if not script_path.exists():
                raise FileNotFoundError(f"스크립트 파일을 찾을 수 없습니다: {script_path}")
            
            cmd = [
                sys.executable,
                str(script_path),
                '--token-file', args.token_file,
                '--split-index', str(split_num)
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    env=env,
                    cwd=str(project_root),
                    check=True,
                    capture_output=False
                )
                logger.info(f"✓ 분할 {split_num}/{args.split_count} 완료")
            
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ 분할 {split_num}/{args.split_count} 실행 오류: {e}")
                # 오류가 있어도 계속 진행
                continue
        
        logger.info(f"\n✅ 모든 분할 실행 완료!")
    
    # 결과 파일 찾기
    logger.info(f"\n📋 결과 파일 수집 중...")
    
    # 출력 디렉토리에서 JSON/CSV 파일 찾기
    buildings_json_files = sorted(output_dir.glob("openup_seoul_gyeonggi_buildings_*_split*.json"))
    buildings_csv_files = sorted(output_dir.glob("openup_seoul_gyeonggi_buildings_*_split*.csv"))
    stores_json_files = sorted(output_dir.glob("openup_seoul_gyeonggi_stores_*_split*.json"))
    stores_csv_files = sorted(output_dir.glob("openup_seoul_gyeonggi_stores_*_split*.csv"))
    expanded_csv_files = sorted(output_dir.glob("openup_seoul_gyeonggi_stores_*_split*_expanded.csv"))
    
    logger.info(f"  건물 JSON: {len(buildings_json_files)}개")
    logger.info(f"  건물 CSV: {len(buildings_csv_files)}개")
    logger.info(f"  매장 JSON: {len(stores_json_files)}개")
    logger.info(f"  매장 CSV: {len(stores_csv_files)}개")
    logger.info(f"  Expanded CSV: {len(expanded_csv_files)}개")
    
    # 병합 수행
    logger.info(f"\n🔗 병합 작업 시작...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 건물 데이터 병합
    if buildings_json_files:
        merged_buildings_json = output_dir / f"openup_seoul_gyeonggi_buildings_merged_{timestamp}.json"
        merge_json_files(buildings_json_files, merged_buildings_json, "data")
    
    if buildings_csv_files:
        merged_buildings_csv = output_dir / f"openup_seoul_gyeonggi_buildings_merged_{timestamp}.csv"
        merge_csv_files(buildings_csv_files, merged_buildings_csv)
    
    # 매장 데이터 병합
    if stores_json_files:
        merged_stores_json = output_dir / f"openup_seoul_gyeonggi_stores_merged_{timestamp}.json"
        merge_json_files(stores_json_files, merged_stores_json, "data")
    
    if stores_csv_files:
        merged_stores_csv = output_dir / f"openup_seoul_gyeonggi_stores_merged_{timestamp}.csv"
        merge_csv_files(stores_csv_files, merged_stores_csv)
    
    # Expanded CSV 병합
    if expanded_csv_files:
        merged_expanded_csv = output_dir / f"openup_seoul_gyeonggi_stores_merged_expanded_{timestamp}.csv"
        merge_csv_files(expanded_csv_files, merged_expanded_csv)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ 모든 작업 완료!")
    logger.info(f"📁 출력 디렉토리: {output_dir}")
    logger.info(f"{'='*80}")


if __name__ == '__main__':
    main()
