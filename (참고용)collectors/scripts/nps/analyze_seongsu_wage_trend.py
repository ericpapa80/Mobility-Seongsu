# -*- coding: utf-8 -*-
"""성수동1가·성수동2가 NPS 평균 임금 변화 추이 분석

연도별 NPS 수집 결과에서 가입자수 가중 평균 임금(월급여추정)을 계산하여
2015~2024년 평균 임금 변화 추이를 정리합니다.

사용법:
  python scripts/nps/analyze_seongsu_wage_trend.py
  python scripts/nps/analyze_seongsu_wage_trend.py --input-dir "경로/연도별데이터"
"""

import sys
import argparse
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

import pandas as pd


def load_yearly_data(input_dir: Path) -> dict[int, pd.DataFrame]:
    """연도별 CSV 로드 (nps_seongsu_YYYY.csv 패턴)"""
    data = {}
    for fp in sorted(input_dir.glob('nps_seongsu_*.csv')):
        try:
            yr = int(fp.stem.replace('nps_seongsu_', ''))
            df = pd.read_csv(fp, encoding='utf-8-sig', low_memory=False)
            if '월급여추정' not in df.columns and '인당금액' in df.columns:
                df['월급여추정'] = df['인당금액'] / 9 * 100
            if '월급여추정' not in df.columns:
                continue
            data[yr] = df
        except Exception:
            pass
    return data


def compute_weighted_avg(df: pd.DataFrame, col: str = '월급여추정', weight_col: str = '가입자수') -> float:
    """가입자수 가중 평균 (해당 col)"""
    if weight_col not in df.columns:
        return df[col].mean()
    w = df[weight_col].fillna(0).replace(0, 1)
    return (df[col] * w).sum() / w.sum()


def main():
    parser = argparse.ArgumentParser(
        description='성수동1가·성수동2가 NPS 평균 임금 변화 추이 분석'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        default=None,
        help='연도별 CSV 폴더 (기본: data/raw/nps/yearly_seongsu)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='보고서 저장 경로 (기본: analysis/output/nps_seongsu_wage_trend.md)'
    )
    parser.add_argument(
        '--output-csv',
        type=str,
        default=None,
        help='CSV 저장 경로 (기본: analysis/output/nps_seongsu_wage_trend.csv)'
    )
    args = parser.parse_args()

    if args.input_dir:
        input_dir = Path(args.input_dir)
    else:
        input_dir = project_root / 'data' / 'raw' / 'nps' / 'yearly_seongsu'

    if not input_dir.exists():
        input_dir = project_root / 'data' / 'raw' / 'nps'
        if not input_dir.exists():
            input_dir.mkdir(parents=True, exist_ok=True)
        print("[안내] 연도별 데이터가 없습니다. 먼저 수집을 실행하세요:")
        print("  python scripts/nps/collect_seongsu_yearly.py")
        sys.exit(1)

    yearly = load_yearly_data(input_dir)
    if not yearly:
        print("[안내] nps_seongsu_*.csv 파일이 없습니다. collect_seongsu_yearly.py 를 먼저 실행하세요.")
        sys.exit(1)

    # 연도별·동별 가중 평균
    rows = []
    for yr in sorted(yearly.keys()):
        df = yearly[yr]
        if '동' not in df.columns and '사업장지번상세주소' in df.columns:
            df['동'] = df['사업장지번상세주소'].apply(
                lambda x: '성수동1가' if pd.notna(x) and '성수동1가' in str(x) else '성수동2가'
            )
        elif '동' not in df.columns and '읍면동코드' in df.columns:
            df['동'] = df['읍면동코드'].apply(
                lambda x: '성수동1가' if str(x) == '114' else '성수동2가'
            )
        elif '동' not in df.columns:
            df['동'] = '성수동 전체'
        for dong in ['성수동1가', '성수동2가']:
            sub = df[df['동'] == dong] if '동' in df.columns else df
            if len(sub) == 0:
                continue
            avg_monthly = compute_weighted_avg(sub, '월급여추정', '가입자수')
            avg_annual = avg_monthly * 12
            cnt = len(sub)
            workers = sub['가입자수'].sum()
            rows.append({
                '연도': yr,
                '동': dong,
                '사업장수': cnt,
                '가입자수': int(workers),
                '평균_월급여추정_원': round(avg_monthly),
                '평균_연봉추정_원': round(avg_annual)
            })

    df_out = pd.DataFrame(rows)

    # 전체(성수동1가+2가) 합산
    combined = []
    for yr in sorted(yearly.keys()):
        df = yearly[yr]
        avg_monthly = compute_weighted_avg(df, '월급여추정', '가입자수')
        avg_annual = avg_monthly * 12
        combined.append({
            '연도': yr,
            '동': '성수동 전체',
            '사업장수': len(df),
            '가입자수': int(df['가입자수'].sum()),
            '평균_월급여추정_원': round(avg_monthly),
            '평균_연봉추정_원': round(avg_annual)
        })
    df_combined = pd.DataFrame(combined)
    df_report = pd.concat([df_out, df_combined], ignore_index=True).sort_values(['연도', '동'])

    # 보고서 작성
    out_path = Path(args.output) if args.output else project_root / 'data' / 'raw' / 'nps' / 'yearly_seongsu' / 'nps_seongsu_wage_trend.md'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        '# 성수동1가·성수동2가 NPS 평균 임금 변화 추이',
        '',
        f'**분석 기준**: 국민연금 가입 사업장 내역 (활성 가입만)',
        f'**대상 지역**: 서울 성동구 성수동1가, 성수동2가',
        f'**임금 지표**: 월급여추정 = 인당금액/9×100 (국민연금 고지금액 기반 추정)',
        '',
        '---',
        '',
        '## 1. 연도별·동별 평균 임금',
        '',
        '| 연도 | 동 | 사업장수 | 가입자수 | 평균 월급여추정(원) | 평균 연봉추정(원) |',
        '|------|-----|---------|---------|-------------------|------------------|'
    ]

    for _, r in df_report.iterrows():
        lines.append(
            f"| {r['연도']} | {r['동']} | {r['사업장수']:,} | {r['가입자수']:,} | {r['평균_월급여추정_원']:,} | {r['평균_연봉추정_원']:,} |"
        )

    lines.extend([
        '',
        '---',
        '',
        '## 2. 성수동 전체 평균 임금 추이 (요약)',
        ''
    ])

    for _, r in df_combined.iterrows():
        lines.append(f"- **{r['연도']}년**: 월평균 {r['평균_월급여추정_원']:,}원, 연봉추정 {r['평균_연봉추정_원']:,}원 (사업장 {r['사업장수']:,}개, 가입자 {r['가입자수']:,}명)")

    lines.extend([
        '',
        '---',
        '',
        '*국민연금 고지금액은 기준소득월액 상한액이 적용되어 실제 소득과 다를 수 있음.*',
        ''
    ])

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # CSV 저장 (연도, 동, 월평균급여, 추정연봉, 사업장수, 가입자수) - 성수동 전체만
    csv_path = Path(args.output_csv) if args.output_csv else project_root / 'data' / 'raw' / 'nps' / 'yearly_seongsu' / 'nps_seongsu_wage_trend.csv'
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df_csv = df_report[df_report['동'] == '성수동 전체'].rename(columns={
        '평균_월급여추정_원': '월평균급여',
        '평균_연봉추정_원': '추정연봉'
    })[['연도', '동', '월평균급여', '추정연봉', '사업장수', '가입자수']]
    df_csv.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f'CSV 저장: {csv_path}')

    # 콘솔 출력
    print()
    print('=' * 70)
    print('성수동1가·성수동2가 NPS 평균 임금 변화 추이')
    print('=' * 70)
    print(df_report.to_string(index=False))
    print()
    print(f'보고서 저장: {out_path}')
    print()


if __name__ == '__main__':
    main()
