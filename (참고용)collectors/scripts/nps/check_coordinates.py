# -*- coding: utf-8 -*-
"""좌표 범위 확인 스크립트"""

import sys
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

csv_path = project_root / "data" / "raw" / "nps" / "nps_20251222_162853" / "nps_20251222_162853.csv"

if csv_path.exists():
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"전체 레코드: {len(df):,}개")
    
    coords = df[df['x'].notna() & df['y'].notna()]
    print(f"좌표 있는 레코드: {len(coords):,}개 ({len(coords)/len(df)*100:.1f}%)")
    
    print(f"\n좌표 범위:")
    print(f"  경도(x): {coords['x'].min():.6f} ~ {coords['x'].max():.6f}")
    print(f"  위도(y): {coords['y'].min():.6f} ~ {coords['y'].max():.6f}")
    
    # 성수동 지역 좌표 범위 (대략적인 범위)
    seongsu_x_min, seongsu_x_max = 127.04, 127.07
    seongsu_y_min, seongsu_y_max = 37.54, 37.55
    
    in_seongsu = coords[
        (coords['x'] >= seongsu_x_min) & (coords['x'] <= seongsu_x_max) &
        (coords['y'] >= seongsu_y_min) & (coords['y'] <= seongsu_y_max)
    ]
    print(f"\n성수동 지역 내 좌표: {len(in_seongsu):,}개 ({len(in_seongsu)/len(coords)*100:.1f}%)")
    print(f"성수동 지역 외 좌표: {len(coords) - len(in_seongsu):,}개")
    
    if len(coords) - len(in_seongsu) > 0:
        print("\n성수동 지역 외 샘플:")
        outside = coords[
            ~((coords['x'] >= seongsu_x_min) & (coords['x'] <= seongsu_x_max) &
              (coords['y'] >= seongsu_y_min) & (coords['y'] <= seongsu_y_max))
        ]
        print(outside[['사업장명', '주소', 'x', 'y']].head(5).to_string())
else:
    print(f"파일을 찾을 수 없습니다: {csv_path}")

