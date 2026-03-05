# 성수동1가·성수동2가 NPS 연도별 수집 및 평균 임금 추이 분석

## 개요

국민연금 가입 사업장 내역(CSV)에서 **성수동1가**, **성수동2가** 지역만 필터링하여 수집하고, 연도별 평균 임금(월급여추정) 변화 추이를 정리합니다.

## 사용 방법

### 1단계: 연도별 데이터 수집

```bash
# 기본 CSV 사용 (설정된 NPS_CSV_PATH 또는 docs/sources/nps/ 기본값)
python scripts/nps/collect_seongsu_yearly.py

# 단일 CSV 지정
python scripts/nps/collect_seongsu_yearly.py --csv "경로/국민연금가입사업장내역.csv"

# 연도별 CSV가 있는 폴더 지정 (파일명에 연도 포함: nps_2015.csv, nps_2016.csv 등)
python scripts/nps/collect_seongsu_yearly.py --csv-dir "경로/연도별CSV폴더"
```

### 2단계: 평균 임금 추이 분석

```bash
python scripts/nps/analyze_seongsu_wage_trend.py
```

출력: `analysis/output/nps_seongsu_wage_trend.md`

## 2015~2024 연도별 데이터 확보 방법

공공데이터포털의 국민연금 가입 사업장 내역은 **월간 스냅샷**으로 제공됩니다. 과거 연도(2015~2024) 데이터를 얻으려면:

1. **공공데이터포털 파일 데이터**
   - [국민연금 가입 사업장 내역](https://www.data.go.kr/data/15083277/fileData.do)
   - 매월 최신 파일만 제공·교체됨
   - **과거 연도 보관**: 매월 다운로드 후 `nps_YYYYMM.csv` 형태로 보관해야 함

2. **오픈API (기준년월 파라미터)**
   - [국민연금 가입 사업장 내역 API](https://www.data.go.kr/data/3046071/openapi.do)
   - `baseYm=201512` 등으로 과거 년월 조회 가능
   - API 키 신청 후 활용

3. **연도별 CSV 폴더 구성 예시**
   - `yearly_nps/` 아래에 `nps_201512.csv`, `nps_201612.csv`, ... 저장
   - `--csv-dir yearly_nps` 로 수집 실행

## 2025년 수집 결과 (현재 기준)

| 구분 | 사업장수 | 가입자수 | 평균 월급여추정 | 평균 연봉추정 |
|------|---------|---------|-----------------|---------------|
| 성수동 전체 | 4,626 | 92,441 | 3,694,699원 | 44,336,387원 |
| 성수동1가 | 1,752 | 30,078 | 3,897,818원 | 46,773,812원 |
| 성수동2가 | 2,874 | 62,363 | 3,596,734원 | 43,160,802원 |

*가입자수 가중 평균 기준*
