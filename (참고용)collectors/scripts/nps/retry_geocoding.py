# -*- coding: utf-8 -*-
"""좌표가 없는 레코드만 다시 지오코딩하는 스크립트"""

import sys
import argparse
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.scraper import NPSScraper
from plugins.nps.geocoder import Geocoder
from core.logger import get_logger

logger = get_logger(__name__)


def retry_geocoding(csv_path: str, output_path: str = None, geocoding_service: str = "kakao", geocoding_delay: float = 0.1):
    """좌표가 없는 레코드만 다시 지오코딩하여 보완
    
    Args:
        csv_path: 원본 CSV 파일 경로
        output_path: 출력 CSV 파일 경로 (없으면 원본 파일 덮어쓰기)
        geocoding_service: 지오코딩 서비스 ("kakao" 또는 "vworld")
        geocoding_delay: API 호출 간 지연 시간 (초)
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return
    
    print("=" * 80)
    print("좌표 보완 지오코딩")
    print("=" * 80)
    print(f"입력 파일: {csv_path}")
    
    # CSV 파일 읽기
    print("\nCSV 파일 로딩 중...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"전체 레코드: {len(df):,}개")
    
    # 좌표가 없는 레코드 찾기
    no_coords_mask = df['x'].isna() | df['y'].isna() | (df['x'] == 0) | (df['y'] == 0)
    no_coords_df = df[no_coords_mask].copy()
    
    if len(no_coords_df) == 0:
        print("✅ 모든 레코드에 좌표가 이미 있습니다!")
        return
    
    print(f"좌표 없는 레코드: {len(no_coords_df):,}개")
    print(f"좌표 있는 레코드: {len(df) - len(no_coords_df):,}개")
    
    # 지오코더 초기화
    print(f"\n지오코딩 서비스: {geocoding_service}")
    geocoder = Geocoder(service=geocoding_service)
    
    # 좌표가 없는 레코드만 지오코딩
    success_count = 0
    fail_count = 0
    
    print("\n지오코딩 시작...")
    for idx, row in no_coords_df.iterrows():
        address = row.get('주소', '')
        business_name = row.get('사업장명', '')
        jibun_address = row.get('사업장지번상세주소', '')
        
        # 주소가 없으면 사업장지번상세주소 사용
        if pd.isna(address) or not str(address).strip() or str(address).strip() == 'nan':
            if pd.isna(jibun_address) or not str(jibun_address).strip() or str(jibun_address).strip() == 'nan':
                fail_count += 1
                logger.debug(f"주소 없음: {business_name}")
                continue
            address = jibun_address
        
        # 상호명과 주소로 지오코딩
        keyword = str(business_name).strip() if not pd.isna(business_name) and str(business_name).strip() and str(business_name).strip() != 'nan' else None
        address_str = str(address).strip()
        
        if not address_str or address_str == 'nan':
            fail_count += 1
            continue
        
        coords = geocoder.geocode(address_str, keyword=keyword, delay=geocoding_delay)
        
        if coords:
            # 원본 DataFrame 업데이트
            df.at[idx, 'x'] = coords.get('x')
            df.at[idx, 'y'] = coords.get('y')
            df.at[idx, 'lon'] = coords.get('lon')
            df.at[idx, 'lat'] = coords.get('lat')
            success_count += 1
        else:
            fail_count += 1
            logger.debug(f"지오코딩 실패: {business_name} - {address_str}")
        
        # 진행 상황 출력
        if (success_count + fail_count) % 10 == 0:
            print(f"진행: {success_count + fail_count}/{len(no_coords_df)} (성공: {success_count}, 실패: {fail_count})")
    
    geocoder.close()
    
    print("\n" + "=" * 80)
    print("지오코딩 완료")
    print("=" * 80)
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"전체 좌표 보유 레코드: {len(df) - len(no_coords_df) + success_count}/{len(df)}개")
    
    # 결과 저장
    if output_path is None:
        output_path = csv_path
    else:
        output_path = Path(output_path)
    
    print(f"\n결과 저장 중: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("✅ 저장 완료!")


def main():
    parser = argparse.ArgumentParser(description='좌표가 없는 레코드만 다시 지오코딩')
    parser.add_argument('csv_path', help='CSV 파일 경로')
    parser.add_argument('--output', '-o', help='출력 CSV 파일 경로 (없으면 원본 덮어쓰기)')
    parser.add_argument('--geocoding-service', choices=['kakao', 'vworld'], 
                       default='kakao', help='지오코딩 서비스 선택')
    parser.add_argument('--geocoding-delay', type=float, default=0.1,
                       help='지오코딩 API 호출 간 지연 시간(초)')
    
    args = parser.parse_args()
    
    retry_geocoding(
        csv_path=args.csv_path,
        output_path=args.output,
        geocoding_service=args.geocoding_service,
        geocoding_delay=args.geocoding_delay
    )


if __name__ == "__main__":
    main()

