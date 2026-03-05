"""변경구분 필드로 이력 확인 가능 여부 테스트."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger

logger = get_logger(__name__)

client = SBIZAPIClient()

print("=" * 60)
print("변경구분(chgGb) 필드로 이력 확인 가능 여부 테스트")
print("=" * 60)

# 최근 날짜들로 테스트하여 실제 데이터가 있는 날짜 찾기
test_dates = []
for days_ago in range(0, 30):
    test_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
    test_dates.append(test_date)

print("\n최근 30일 중 데이터가 있는 날짜 찾는 중...")

found_data = False
for date_str in test_dates:
    try:
        stores = client.get_all_stores_by_date(date_str)
        
        if stores and len(stores) > 0:
            found_data = True
            print(f"\n✓ 데이터 발견: {date_str}")
            print(f"  변경된 업소 수: {len(stores):,}개")
            
            # 변경구분 필드 분석
            chg_gb_counts = {}
            chg_dt_counts = {}
            sample_stores = []
            
            for store in stores[:100]:  # 처음 100개만 분석
                chg_gb = store.get('chgGb', '').strip()
                chg_dt = store.get('chgDt', '').strip()
                
                chg_gb_counts[chg_gb] = chg_gb_counts.get(chg_gb, 0) + 1
                if chg_dt:
                    chg_dt_counts[chg_dt] = chg_dt_counts.get(chg_dt, 0) + 1
                
                if len(sample_stores) < 5:
                    sample_stores.append({
                        'bizesId': store.get('bizesId'),
                        'bizesNm': store.get('bizesNm'),
                        'chgGb': chg_gb,
                        'chgDt': chg_dt,
                        'adongNm': store.get('adongNm')
                    })
            
            print(f"\n변경구분(chgGb) 분포:")
            for chg_gb, count in sorted(chg_gb_counts.items()):
                meaning = {
                    'C': '신규 개업',
                    'U': '정보 수정',
                    'D': '폐업/삭제'
                }.get(chg_gb, '알 수 없음')
                print(f"  {chg_gb}: {count}개 ({meaning})")
            
            if chg_dt_counts:
                print(f"\n변경일자(chgDt) 분포 (샘플):")
                for chg_dt, count in sorted(chg_dt_counts.items())[:5]:
                    print(f"  {chg_dt}: {count}개")
            
            print(f"\n샘플 업소 (처음 5개):")
            for i, store in enumerate(sample_stores, 1):
                print(f"  {i}. {store['bizesNm']} ({store['bizesId']})")
                print(f"     변경구분: {store['chgGb']}, 변경일자: {store['chgDt']}")
                print(f"     행정동: {store['adongNm']}")
            
            # 성수동 업소 확인
            seongsu_dongs = ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']
            seongsu_stores = [s for s in stores if s.get('adongNm') in seongsu_dongs]
            if seongsu_stores:
                print(f"\n성수동 업소: {len(seongsu_stores)}개")
                for store in seongsu_stores[:3]:
                    print(f"  - {store.get('bizesNm')} ({store.get('chgGb')})")
            
            break
            
    except Exception as e:
        continue

if not found_data:
    print("\n최근 30일 내 데이터가 있는 날짜를 찾지 못했습니다.")
    print("\n변경구분(chgGb) 필드 설명:")
    print("  - C: 신규 개업 (Create)")
    print("  - U: 정보 수정 (Update)")
    print("  - D: 폐업/삭제 (Delete)")
    print("\n변경일자(chgDt) 필드:")
    print("  - 해당 변경이 발생한 날짜")
    print("\n제약사항:")
    print("  - storeListByDate는 해당 날짜에 변경된 업소만 조회합니다")
    print("  - 전체 업소 목록을 얻으려면 매일 정기적으로 수집해야 합니다")
    print("  - 또는 CSV 파일을 활용하여 연도별 전체 목록을 얻을 수 있습니다")

client.close()
