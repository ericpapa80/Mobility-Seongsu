# SGIS 결합조건 수집 (비공개·세션 의존)

인구·가구·주택 **결합조건**으로 집계구별 건수를 조회한 뒤, 집계구 경계와 결합해 GeoJSON을 만드는 **최종 실행 스크립트**입니다.  
**공식 OpenAPI가 아닌** 대화형통계지도용 ServiceAPI(`fusionstats.json`)와 OpenAPI3 경계 API를 사용하며, **Access Token**과 **Fusion 세션(쿠키/토큰)** 이 필요합니다.

## 최종 파일

| 파일 | 설명 |
|------|------|
| **run_fusion_gui.py** | GUI로 Access Token·adm_cd 입력 후, 연령(선택)·세대구성(다중)·주택유형(다중)·연면적(선택)을 고르면, 경계 수집 + fusion 수집 + 결합이 한 프로세스로 실행되고 `data/raw/sgis_fusion/` 아래에 GeoJSON이 저장됩니다. |

- **수집 순서**: **1) 연령 단독** — age_*, age_total만 요청(combine_base=population, fusion_query_type=population_household, hh/ht/ha 미포함). **2) age 조건 하에** hh_*, hh_total, ht, ha 수집.
- **연령·세대구성**: 연령은 **연령대별 통합**(`age_0_9`, `age_20_29`, …, `age_70+` = 선택 세대구성 합산 인구), 세대구성은 **세대구성별 합계**(`hh_A0`, `hh_01`, … = 선택 연령 범위 내). **age_total**(연령 합계), **hh_total**(가구수, age 조건 하에 `combine_base=household` 1회 호출 per adm_cd). 동일 연령 범위로 조회하므로 인구(age_total) ≥ 가구수(hh_total).
- **세대구성 코드 (household_type)**: `A0`=1인가구, `01`=1세대가구, `02`=2세대가구, `03`=3세대가구, `04`=4세대가구, `05`=5세대이상가구, `B0`=비혈연가구. hh_total 호출 시 GUI에서 선택한 코드를 **쉼표로 나열**하여 전송 (예: `household_type=01,02,03,04,A0,B0` 또는 전 항목 선택 시 `A0,01,02,03,04,05,B0`).
- 컬럼 생성 규칙: **연령×세대구성** = house_type·house_area_cd 없이 세대구성별 호출, **주택유형 컬럼** = 연령 범위만 고정·house_area_cd 없이(대표 세대구성 1개), **연면적 컬럼** = 연령 범위만 고정·house_type 없이.
- **주택유형·연면적 포함** 체크 해제 시: `fusion_query_type=population_household`, `combine_base=household` 로만 요청하며 `house_type`·`house_area_cd` 를 보내지 않음. 연령(age_*), 세대구성(hh_*), age_total, hh_total 컬럼만 산출.
- **1인가구(A0) 단일 + 주택포함** 수집 시: 1차로 연령만 `population_household` 요청 → age_*_A0, hh_A0, age_total. 2차로 `population_household_house` 요청 → ht01~06, ha01~09. **오피스텔 보정**: ht07 = hh_total(가구수) − ht_total(2차), ha10 = hh_total − ha_total(2차) 로 추정 후, ht_total/ha_total 재계산.
- **0값 보정**: 프라이버시/소수보호로 4 이하가 0으로 나오는 값에 대해, 0인 항목과 인접 비영(0이 아닌) 항목을 묶어 결합 호출한 값이 5 이상이면 그 차이로 0을 보정합니다. **연령(age)**은 세대구성별로, **세대구성(hh)**은 2개 이상 선택 시 세대구성 차원으로, **주택유형(ht)**·**연면적(ha)**은 기존과 동일하게 적용. (예: ha05=0, ha06=5 → ha05+ha06 호출해 7이면 ha05=2로 치환.)
- 이전·CLI·실험용 스크립트는 `old/` 폴더에 보관되어 있습니다.

## 환경 설정

**경계 API**: 입력창 없음. **collectors/.env**에만 저장하며, 형식은 **collectors/env_template.txt**와 같음.  
- **SGIS_OPENAPI_ACCESS_TOKEN** = 발급받은 액세스 토큰, 또는  
- **SGIS_CONSUMER_KEY** + **SGIS_CONSUMER_SECRET** 으로 실행 시 토큰 발급.

**Fusion API**: Fusion 토큰/쿠키는 **유효 기간이 약 하루**이므로 `.env`에 두지 않고 **GUI 입력란에 직접 입력**하는 방식을 권장합니다. 입력한 값은 `collectors/.last_fusion_cookie.txt`에 저장되어 **다음 GUI 실행 시 그대로 채워집니다.** (필요 시 `.env`의 `SGIS_FUSION_ACCESS_TOKEN` 또는 `SGIS_FUSION_COOKIE`를 보조로 사용할 수 있습니다.)

토큰/쿠키 획득: https://sgis.mods.go.kr 로그인 → 대화형통계지도 → 인구주택총조사 → 조건설정(결합조건) 진입 → F12 → Application → Cookies → `accessToken` 복사.

## 실행

```bash
# collectors 폴더 기준
cd D:\VSCODE_PJT\html_of_infinite-ver3\framework\collectors

python scripts/sgis_fusion/run_fusion_gui.py
```

GUI에서 adm_cd(8자리, 쉼표로 복수 가능)·Fusion Cookie/Token, 연령/세대구성/주택유형/연면적을 선택한 뒤 **「수집 실행」** 을 누르면, 로그가 실시간으로 출력되고 완료 후 출력 폴더 경로가 표시됩니다. (경계 API 토큰은 .env에서만 읽음.)

## 출력 구조

수집·결합 결과는 **항상** `data/raw/sgis_fusion/` 아래에만 저장됩니다.  
**폴더명·GeoJSON 파일명**은 GUI에서 선택한 세대구성·연령 범위를 반영한 **run_slug**로 생성됩니다. 세대구성 1개 선택 시 `1person`, `1gen` 등 해당 코드 slug, **2개 이상 선택 시 `multi`** + 연령 범위(예: 1인가구만 → `sgis_fusion_1person_20_49_YYYYMMDD_HHMMSS`, 전 세대구성 → `sgis_fusion_multi_20_49_YYYYMMDD_HHMMSS`, `tract_1person_20_49.geojson` / `tract_multi_20_49.geojson`).

```
data/raw/sgis_fusion/
└── sgis_fusion_{run_slug}_YYYYMMDD_HHMMSS/
    ├── tract_{run_slug}.geojson  # 최종 결합 GeoJSON (경계 + age_*, hh_*, age_total, hh_total, ht/ha 컬럼)
    ├── boundary_tract.geojson     # 집계구 경계만 (WGS84)
    ├── legend.json               # 필드 한글 라벨
    └── collection_summary.json   # 수집 요약 + GUI에서 체크한 항목(라벨 포함)
```

## 참고 문서

- 결합조건 수집 가능 여부: `docs/sources/sgis/결합조건_수집_가능여부.md`
- 요청 파라미터(결합조건) 범주별 의미: `docs/sources/sgis/fusionstats_params_guide.md`

## 주의

- Fusion API는 **비공개**이며, 스펙 변경·중단 가능성이 있습니다.
- 세션 만료 시 토큰/쿠키를 다시 발급해야 합니다.
- 이용약관·자동 수집 허용 범위는 사용자가 확인하세요.
