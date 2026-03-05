# -*- coding: utf-8 -*-
"""성수동 필터링 직접 테스트"""

import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.scraper import NPSScraper

# 성수동 필터링 테스트
scraper = NPSScraper()
filter_text = "성수동"

print(f"필터 텍스트: {filter_text}")
print(f"필터 텍스트 인코딩 확인: {repr(filter_text)}")

result = scraper.scrape(
    filter_address=filter_text,
    filter_active_only=True,
    save_json=True,
    save_csv=True
)

print(f"\n수집 완료: {result['total_count']}개 사업장")

if result['total_count'] > 0:
    print("\n샘플 데이터:")
    records = result['data']['records'][:3]
    for r in records:
        print(f"  - {r.get('사업장명', '')}: {r.get('주소', '')}")

