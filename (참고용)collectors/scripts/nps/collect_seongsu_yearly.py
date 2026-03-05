# -*- coding: utf-8 -*-
"""성수동1가·성수동2가 NPS 연도별 수집 (2015~2024)

연도별 CSV 파일에서 성수동1가, 성수동2가 사업장 데이터를 필터링하여 수집합니다.
평균 임금 변화 추이 분석을 위해 연도별 데이터를 별도 폴더에 저장합니다.

사용법:
  1) 연도별 CSV가 있는 경우:
     python scripts/nps/collect_seongsu_yearly.py --csv-dir "경로/연도별CSV폴더"
     - 폴더 내 파일명에 연도가 포함되어야 함 (예: nps_2015.csv, 국민연금_201612.csv)

  2) 단일 CSV 사용 (해당 월 스냅샷만):
     python scripts/nps/collect_seongsu_yearly.py --csv "경로/국민연금가입사업장내역.csv"

  3) 기본 경로 사용:
     python scripts/nps/collect_seongsu_yearly.py
     - NPS_CSV_PATH 환경변수 또는 config 기본값 사용
"""

import sys
import argparse
import re
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.scraper import NPSScraper
from core.logger import get_logger
import pandas as pd

logger = get_logger(__name__)

# 성수동1가 법정동코드(읍면동코드) 114, 성수동2가 115
SEONGSU1_EMD = '114'
SEONGSU2_EMD = '115'


def extract_year_from_path(path: Path) -> int | None:
    """파일 경로 또는 이름에서 연도 추출 (4자리)"""
    name = path.stem + path.suffix
    match = re.search(r'(20\d{2})', name)
    return int(match.group(1)) if match else None


STANDARD_COLUMNS = [
    '자료생성년월', '사업장명', '사업자등록번호', '가입상태', '우편번호',
    '사업장지번상세주소', '주소', '고객법정동주소코드', '고객행정동주소코드',
    '시도코드', '시군구코드', '읍면동코드',
    '사업장형태구분코드', '업종코드', '업종코드명',
    '적용일자', '재등록일자', '탈퇴일자',
    '가입자수', '금액', '신규', '상실'
]


def collect_from_csv(
    csv_path: Path,
    filter_active: bool = True
) -> pd.DataFrame:
    """단일 CSV에서 성수동1가·성수동2가만 필터링하여 DataFrame 반환"""
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            df = pd.read_csv(csv_path, encoding=enc, low_memory=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Failed to read {csv_path}")
    if len(df.columns) >= len(STANDARD_COLUMNS):
        df = df.iloc[:, :len(STANDARD_COLUMNS)]
    df.columns = STANDARD_COLUMNS[:len(df.columns)]
    if filter_active:
        df = df[df['가입상태'] == 1]

    # 성수동1가, 성수동2가 필터: 서울 성동구만 (사업장지번상세주소에 '성수동1가'/'성수동2가' 포함)
    # 읍면동코드 114/115는 전국 중복 사용되므로 주소 문자열 기준으로만 필터
    def is_seongsu(row):
        jibun = str(row.get('사업장지번상세주소', '') or '')
        if '서울' not in jibun and '성동' not in jibun:
            return False
        return '성수동1가' in jibun or '성수동2가' in jibun

    df = df[df.apply(is_seongsu, axis=1)]

    # 파생 필드
    df['인당금액'] = df['금액'] / df['가입자수'].replace(0, 1)
    df['월급여추정'] = df['인당금액'] / 9 * 100
    df['연간급여추정'] = df['월급여추정'] * 12

    def get_dong(row):
        j = str(row.get('사업장지번상세주소', '') or '')
        return '성수동1가' if '성수동1가' in j else '성수동2가'

    df['동'] = df.apply(get_dong, axis=1)
    return df


def main():
    parser = argparse.ArgumentParser(
        description='성수동1가·성수동2가 NPS 연도별 수집 (2015~2024)'
    )
    parser.add_argument(
        '--csv-dir',
        type=str,
        default=None,
        help='연도별 CSV가 있는 폴더 경로 (파일명에 연도 포함)'
    )
    parser.add_argument(
        '--csv',
        type=str,
        default=None,
        help='단일 CSV 파일 경로 (해당 월만 처리)'
    )
    parser.add_argument(
        '--years',
        type=str,
        default='2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025',
        help='대상 연도 (쉼표 구분)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='출력 디렉터리 (기본: data/raw/nps/yearly_seongsu)'
    )
    args = parser.parse_args()

    out_base = project_root / 'data' / 'raw' / 'nps'
    if args.output_dir:
        out_base = Path(args.output_dir)
    out_base = out_base / 'yearly_seongsu'
    out_base.mkdir(parents=True, exist_ok=True)

    target_years = [int(y.strip()) for y in args.years.split(',')]
    results = []

    # 1) 연도별 CSV 디렉터리
    if args.csv_dir:
        csv_dir = Path(args.csv_dir)
        if not csv_dir.exists():
            print(f"[오류] CSV 폴더가 없습니다: {csv_dir}")
            sys.exit(1)
        raw_files = [f for f in csv_dir.glob('*.csv') if not f.name.startswith('nps_seongsu_')]
        raw_files += [f for f in csv_dir.glob('*.CSV') if not f.name.startswith('nps_seongsu_')]
        for fp in sorted(raw_files):
            yr = extract_year_from_path(fp)
            if yr and yr in target_years:
                try:
                    df = collect_from_csv(fp)
                    if len(df) == 0:
                        print(f"  {yr}년: 데이터 없음")
                        continue
                    out_file = out_base / f'nps_seongsu_{yr}.csv'
                    df.to_csv(out_file, index=False, encoding='utf-8-sig')
                    results.append({'year': yr, 'count': len(df), 'file': str(out_file)})
                    print(f"  {yr}년: {len(df):,}개 사업장 저장 → {out_file.name}")
                except Exception as e:
                    logger.warning(f"{fp}: {e}")

    # 2) 단일 CSV
    elif args.csv:
        fp = Path(args.csv)
        if not fp.exists():
            print(f"[오류] CSV 파일이 없습니다: {fp}")
            sys.exit(1)
        yr = extract_year_from_path(fp)
        if not yr:
            ym = datetime.now().strftime('%Y')
            yr = int(ym)
        try:
            df = collect_from_csv(fp)
            if len(df) == 0:
                print(f"  성수동1가·2가 데이터가 없습니다.")
                sys.exit(0)
            out_file = out_base / f'nps_seongsu_{yr}.csv'
            df.to_csv(out_file, index=False, encoding='utf-8-sig')
            results.append({'year': yr, 'count': len(df), 'file': str(out_file)})
            print(f"  {yr}년: {len(df):,}개 사업장 저장 → {out_file.name}")
        except Exception as e:
            logger.error(e)
            raise

    # 3) 기본 CSV (config)
    else:
        from config.scrapers.nps import NPSConfig
        default_path = NPSConfig.get_default_csv_path()
        if not default_path or not Path(default_path).exists():
            print("[안내] 기본 NPS CSV가 없습니다. --csv 또는 --csv-dir를 지정하세요.")
            print("  예: --csv \"docs/sources/nps/국민연금공단_국민연금 가입 사업장 내역_20251124.csv\"")
            sys.exit(1)
        fp = Path(default_path)
        yr = extract_year_from_path(fp)
        if not yr:
            yr = int(datetime.now().strftime('%Y'))
        try:
            df = collect_from_csv(fp)
            if len(df) == 0:
                print(f"  성수동1가·2가 데이터가 없습니다.")
                sys.exit(0)
            out_file = out_base / f'nps_seongsu_{yr}.csv'
            df.to_csv(out_file, index=False, encoding='utf-8-sig')
            results.append({'year': yr, 'count': len(df), 'file': str(out_file)})
            print(f"  {yr}년: {len(df):,}개 사업장 저장 → {out_file.name}")
        except Exception as e:
            logger.error(e)
            raise

    print()
    print("=" * 60)
    print("수집 완료")
    print("=" * 60)
    print(f"출력 폴더: {out_base}")
    print(f"처리된 연도: {len(results)}개")
    if results:
        for r in results:
            print(f"  - {r['year']}년: {r['count']:,}개")
    print()
    print("평균 임금 추이 분석: python scripts/nps/analyze_seongsu_wage_trend.py")


if __name__ == '__main__':
    main()
