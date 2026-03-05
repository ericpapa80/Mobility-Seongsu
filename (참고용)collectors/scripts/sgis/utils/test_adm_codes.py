"""행정구역 코드 테스트"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.sgis.scraper import SGISScraper

codes_to_test = [
    '11200', '11560', '11220', '11230', '11240', '11250'
]

scraper = SGISScraper()

for code in codes_to_test:
    try:
        result = scraper.scrape(year=2023, adm_cd=code, save_json=False, save_csv=False)
        data = result.get('data', {})
        
        if 'errMsg' in data:
            print(f"{code}: {data.get('errMsg')}")
        else:
            items = data.get('result', [])
            if items:
                addresses = [item.get('naddr', '') for item in items[:5] if item.get('naddr')]
                gu_names = set([addr.split()[1] if len(addr.split()) > 1 else '' for addr in addresses if addr])
                print(f"{code}: {len(items)}개 항목, 구 이름: {gu_names}")
            else:
                print(f"{code}: 데이터 없음")
    except Exception as e:
        print(f"{code}: 오류 - {e}")

scraper.close()

