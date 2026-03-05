"""성수동 필터링 테스트"""

import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.scraper import NPSScraper
import pandas as pd

# CSV 파일 직접 확인
csv_path = project_root / "docs" / "sources" / "nps" / "국민연금공단_국민연금 가입 사업장 내역_20251124.csv"
df = pd.read_csv(csv_path, encoding='cp949', nrows=10000)

# 컬럼명 확인
print("컬럼명:", df.columns.tolist()[:10])

# 주소 컬럼 확인 (7번째 인덱스)
if len(df.columns) > 6:
    address_col = df.columns[6]
    print(f"\n주소 컬럼: {address_col}")
    
    # 성수동 포함 확인
    seongsu = df[df[address_col].astype(str).str.contains('성수', na=False)]
    print(f"성수 포함 레코드: {len(seongsu)}개")
    
    if len(seongsu) > 0:
        print("\n샘플:")
        print(seongsu[[df.columns[1], address_col]].head(3))

# 스크래이퍼 테스트
print("\n" + "="*50)
print("스크래이퍼 테스트")
print("="*50)

scraper = NPSScraper()
result = scraper.scrape(
    filter_address="성수동",
    filter_active_only=True,
    save_json=False,
    save_csv=False
)

print(f"수집된 레코드: {result['total_count']}개")

