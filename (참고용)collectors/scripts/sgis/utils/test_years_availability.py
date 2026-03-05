"""2016-2023 연도별 데이터 수집 가능 여부 테스트"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.sgis.scraper import SGISScraper
from core.logger import get_logger

logger = get_logger(__name__)

# 테스트할 연도 목록
years = list(range(2016, 2024))  # 2016~2023

# 성동구 행정구역 코드 (기존 데이터와 동일)
adm_cd = "11200"  # 성동구

print("=" * 80)
print("2016-2023 연도별 데이터 수집 가능 여부 테스트")
print("=" * 80)
print(f"테스트 지역: 성동구 (adm_cd={adm_cd})")
print(f"테스트 연도: {years[0]} ~ {years[-1]}\n")

scraper = SGISScraper()
available_years = []
unavailable_years = []

for year in years:
    print(f"테스트 중: {year}년...", end=" ")
    try:
        # 작은 테스트 요청 (no-save 모드)
        result = scraper.scrape(
            theme_cd=0,
            year=year,
            adm_cd=adm_cd,
            data_type=3,
            save_json=False,
            save_csv=False
        )
        
        # 데이터 확인
        data = result.get('data', {})
        items = data.get('result', [])
        
        if items and len(items) > 0:
            print(f"✅ 가능 ({len(items)}개 항목)")
            available_years.append(year)
        else:
            print(f"⚠️ 데이터 없음")
            unavailable_years.append(year)
            
    except Exception as e:
        print(f"❌ 오류: {str(e)[:50]}")
        unavailable_years.append(year)
    
    # API 부하 방지를 위한 짧은 대기
    import time
    time.sleep(0.5)

scraper.close()

print("\n" + "=" * 80)
print("테스트 결과 요약")
print("=" * 80)
print(f"✅ 수집 가능한 연도 ({len(available_years)}개): {available_years}")
if unavailable_years:
    print(f"❌ 수집 불가능한 연도 ({len(unavailable_years)}개): {unavailable_years}")
else:
    print("✅ 모든 연도 수집 가능!")

print("\n" + "=" * 80)
print("결론")
print("=" * 80)
if len(available_years) >= 5:
    print(f"✅ 2016-2023 연도별 시계열 데이터 수집이 가능합니다.")
    print(f"   수집 가능한 연도: {len(available_years)}개")
else:
    print(f"⚠️ 일부 연도만 수집 가능합니다.")
    print(f"   수집 가능한 연도: {len(available_years)}개")

