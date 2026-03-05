# 건축Hub 수집 스크립트

건축서비스산업 정보체계(건축Hub) OpenAPI로 **건축물대장·건축인허가** 데이터를 수집합니다.

## 사전 준비

- `.env`에 **건축Hub_API_KEY** 설정 (공공데이터포털에서 건축물대장/건축인허가 API 활용신청 후 발급)
- **시군구코드·법정동코드**: [행정표준코드관리시스템](https://www.code.go.kr) → 코드검색 → 법정동코드목록조회에서 조회

### 성동구·성수동 예시

- 시군구코드: **11200** (서울특별시 성동구)
- 성수동 법정동코드(5자리): **11400**(성수동1가), **11500**(성수동2가) — code.go.kr에서 확인 가능

## 사용 방법

### 1. 성수동 전용 일괄 수집 (권장)

성수동1가·성수동2가를 수집한 뒤 **대장/인허가별로 병합**하여 한 타임스탬프 폴더에만 저장 (raw·processed 하위 폴더 없음):

```bash
cd collectors
python scripts/archhub/collect_seongsu.py --seongsu-only
```

- 출력: `data/raw/archhub/archhub_seongsu_{YYYYMMDD_HHMMSS}/` (해당 폴더 바로 아래만 사용)
  - `bldrgst_getBrBasisOulnInfo_11200_seongsu_{ts}.json` / `.csv` — 건축물대장 기본개요 (성수동 전체 병합)
  - `archpms_getApBasisOulnInfo_11200_seongsu_{ts}.json` / `.csv` — 건축인허가 기본개요 (성수동 전체 병합)
  - `seongsu_collection_summary_{ts}.json` — 수집 요약(동별·오퍼레이션별 건수, 파일 목록)

### 2. 성동구·지정 법정동 수집

```bash
cd collectors
python scripts/archhub/collect_seongsu.py --bjdong 11400 11500
python scripts/archhub/collect_seongsu.py --service archpms --operation getApBasisOulnInfo --bjdong 11400
```

- `--sigungu`: 시군구코드 (기본 11200 = 성동구)
- `--bjdong`: 법정동코드 하나 이상 (공백 구분)
- `--service`: bldrgst | archpms (기본 bldrgst)
- `--operation`: 오퍼레이션명 (기본 getBrBasisOulnInfo)
- `--output-dir`: 출력 디렉터리 (기본 data/raw/archhub)

### 3. Python에서 스크래퍼 직접 사용

```python
from pathlib import Path
from plugins.archhub import ArchHubScraper

scraper = ArchHubScraper(output_dir=Path("data/raw/archhub"))

# 건축물대장 기본개요: 성동구 한 법정동 전체 수집
result = scraper.scrape(
    service="bldrgst",
    operation="getBrBasisOulnInfo",
    sigungu_cd="11200",
    bjdong_cd="10400",
    num_of_rows=100,
    delay_seconds=0.3,
    save_json=True,
    save_csv=True,
)
print(result["total_count"], result["files"])
scraper.close()
```

## 오퍼레이션 (일부)

- **건축물대장**: getBrBasisOulnInfo(기본개요), getBrRecapTitleInfo(총괄표제부), getBrTitleInfo(표제부), getBrFlrOulnInfo(층별개요), …
- **건축인허가**: getApBasisOulnInfo(기본개요), getApDongOulnInfo(동별개요), getApFlrOulnInfo(층별개요), …

전체 목록은 `config/scrapers/archhub.py` 및 [수집체계_요약.md](../../docs/sources/건축hub/수집체계_요약.md) 참고.

## 출력

- **성수동 전용**(`--seongsu-only`): `data/raw/archhub/archhub_seongsu_{타임스탬프}/` 폴더 **바로 아래**에만 파일 저장 (raw/processed 없음). 대장·인허가별 병합 파일: `{service}_{operation}_11200_seongsu_{ts}.json` / `.csv`, `seongsu_collection_summary_{ts}.json`
- **일반 모드**: `data/raw/archhub/` (또는 `--output-dir` 지정), 파일명: `{service}_{operation}_{sigunguCd}_{bjdongCd}_{timestamp}.json` / `.csv`

## 제한

- 1회 요청 최대 100건 → 스크래퍼가 totalCount 기준으로 페이지 자동 반복
- 시군구·법정동 단위 조회만 지원 (전역 검색 아님)
