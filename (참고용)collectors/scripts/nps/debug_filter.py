# -*- coding: utf-8 -*-
"""필터링 디버깅"""

import sys
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.scraper import NPSScraper

# CSV 직접 읽기
csv_path = project_root / "docs" / "sources" / "nps" / "국민연금공단_국민연금 가입 사업장 내역_20251124.csv"
df_raw = pd.read_csv(csv_path, encoding='cp949', low_memory=False, nrows=100000)

print(f"원본 레코드 수: {len(df_raw)}")
print(f"원본 컬럼: {df_raw.columns.tolist()[:7]}")

# 주소 컬럼 확인 (7번째 인덱스)
if len(df_raw.columns) > 6:
    addr_col = df_raw.columns[6]
    print(f"\n주소 컬럼명: {addr_col}")
    
    # 성수동 포함 확인
    seongsu_raw = df_raw[df_raw[addr_col].astype(str).str.contains('성수', na=False)]
    print(f"원본에서 성수 포함: {len(seongsu_raw)}개")
    if len(seongsu_raw) > 0:
        print(f"샘플 주소: {seongsu_raw[addr_col].iloc[0]}")

# 스크래이퍼로 전처리
scraper = NPSScraper()
df_processed = scraper._preprocess_data(df_raw.copy())

print(f"\n전처리 후 레코드 수: {len(df_processed)}")
print(f"전처리 후 컬럼: {df_processed.columns.tolist()[:10]}")

if '주소' in df_processed.columns:
    # 성수동 포함 확인
    seongsu_processed = df_processed[df_processed['주소'].astype(str).str.contains('성수', na=False)]
    print(f"전처리 후 성수 포함: {len(seongsu_processed)}개")
    if len(seongsu_processed) > 0:
        print(f"샘플 주소: {seongsu_processed['주소'].iloc[0]}")
        
        # 필터 함수 테스트
        filter_text = "성수동"
        def contains_filter(addr):
            if pd.isna(addr):
                return False
            return filter_text in str(addr)
        
        mask = df_processed['주소'].apply(contains_filter)
        print(f"apply 함수로 필터링: {mask.sum()}개")
        
        # 활성 사업장만
        df_active = df_processed[df_processed['가입상태'] == 1]
        mask_active = df_active['주소'].apply(contains_filter)
        print(f"활성 사업장 중 성수동: {mask_active.sum()}개")

