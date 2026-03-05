# VWorld 건물 레이어와 ArchHub 건축물대장(부속지번) 결합 방안

본 문서는 아래 두 공간·속성 데이터를 연결하는 방안을 정리한 것입니다.

| 구분 | 파일 경로 | 설명 |
|------|-----------|------|
| **VWorld** | `collectors/data/raw/vworld/vworld_seongsu_20260127_134933/seongsu_lt-c-spbd_20260127_134933.json` | 건축물대장 총괄표제부 기반 **건물 폴리곤** (GeoJSON, 도로명·지번·PNU 등) |
| **ArchHub** | `collectors/data/raw/archhub/archhub_seongsu_20260127_152635/bldrgst_getBrAtchJibunInfo_11200_seongsu_20260127_152635.json` | 건축물대장 **부속지번** 정보 (건물명, 대지위치, 도로명주소, mgmBldrgstPk 등) |

참고한 외부 자료는 다음과 같습니다.

- [RA 공공 데이터 소개](https://help.analytics.rsquareon.com/ko/articles/%EA%B3%B5%EA%B3%B5-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EC%86%8C%EA%B0%9C-36534bf4) — 필지(지번)·PNU 기반 공공데이터 구축, 토지특성정보·건축물대장 관계
- [브런치 @data/24](https://brunch.co.kr/@data/24) — 공공데이터 활용 관련 참고(선택)
- [PublicDataReader - 건축물대장데이터 조회하기](https://wooiljeong.github.io/python/public_data_reader_03/) — 국토교통부 건축물대장 서비스 구조, 시군구/법정동코드, 총괄표제부·표제부 관계

---

## 1. 공공 데이터 관점에서의 배경 (참고 URL 요약)

### 1.1 필지(지번) 단위 공공 데이터 (RA 공공 데이터 소개)

- 공공 데이터는 **필지(지번 주소)** 단위로 구성되며, **지번 주소(PNU)** 기반으로 토지/건물/임차인/실거래/등기 등이 연결된다.
- **토지**: 국토교통부 [토지특성정보](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=NA&dsId=4) 기반, 반기별 업데이트.
- **건물**: 완공 건물은 **건축물대장 총괄표제부·일반표제부**, 공급예정은 건축인허가, 멸실은 폐쇄말소대장 기반.
- 총괄표제부에 연면적이 있으면 그 값을 쓰고, 없으면 일반표제부 중 연면적 최대인 것을 기준으로 하며, 층·승강기수는 일반표제부들을 합산·적용하는 방식으로 정리된 사례가 있다.

이를 현재 프로젝트에 대입하면:

- **VWorld `lt-c-spbd`** = 토지특성정보/건축물대장 계열의 **건물 폴리곤**(총괄표제부 단위 공간 데이터).
- **ArchHub `getBrAtchJibunInfo`** = 같은 건축물대장 체계의 **부속지번** 정보(무좌표 속성).

즉, “같은 건물”을 공간(VWorld)과 대장 속성(ArchHub) 두 소스로 보는 구조이다.

### 1.2 건축물대장 서비스 구조 (PublicDataReader 문서)

- 국토교통부 건축물대장정보는 **기본개요, 총괄표제부, 표제부, 층별개요, 부속지번, 전유부** 등 대장 유형별로 나뉜다.
- 조회 시 **시군구코드(5자리)·법정동코드(5자리)·본번·부번**이 핵심 입력이며, **총괄표제부**는 건물 단위 요약, **표제부**는 동·호 등 세부 정보와 연결된다.
- 테이블 관계: **총괄표제부 → 표제부 → 전유부** 등 상하위 관계가 있고, **부속지번**은 한 건물에 여러 지번이 연결되는 1:N 구조다.

따라서:

- VWorld 건물 한 폴리곤 = 총괄표제부 1건에 대응되는 공간 1건.
- ArchHub 부속지번 N건 = 같은 건물(동일 mgmBldrgstPk)에 대한 지번 N건.
- **결합 목표**: VWorld 건물 1건에, 해당 건물의 대장·부속지번 정보(ArchHub)를 1:1 또는 1:N으로 붙이는 것.

---

## 1.3 PublicDataReader의 건축물대장 연결관계 (ERD·테이블 관계)

[PublicDataReader - 건축물대장데이터 조회하기](https://wooiljeong.github.io/python/public_data_reader_03/) 문서에는 **국토교통부 건축물대장정보**의 테이블 관계도(ERD)와 연결 방식이 정리되어 있다. 건축Hub·공공데이터포털 건축물대장 API는 동일한 국토교통부 원천이므로, 같은 구조와 연결키를 사용한다.

### 테이블 관계도(ERD) 요약

- 문서 내 **테이블관계도** 이미지: [building_talbe_erd.png](https://wooiljeong.github.io/assets/img/common/building_talbe_erd.png)  
  (정우일 블로그 / PublicDataReader 문서에서 “테이블관계도” 절 참고)
- **연결키**: 각 테이블은 **관리건축물대장PK**(건축Hub 응답의 `mgmBldrgstPk`)로 연결된다.  
  시군구코드·법정동코드·본번·부번 등 주소 기반으로 조회한 뒤, 동일 PK로 대장 유형별 데이터를 조인할 수 있다.

### 건축물대장 테이블 10종과 계층

| 구분(대장 유형) | 설명 | 관계 |
|----------------|------|------|
| 기본개요 | 건축물대장 대장종류별 관리 | - |
| **총괄표제부** | 총괄표제부 관리 (여러 동 요약) | 상위 |
| **표제부** | 건축물의 표제부(동 단위) 관리 | 총괄표제부 하위 |
| 층별개요 | 건축물의 층별 개요 | 1:N |
| **전유부** | 건축물의 호별(세대별) 개요 | 표제부 하위 |
| 전유공용면적 | 호별 전유/공용 부분 | 1:N |
| **부속지번** | 건축물의 관련 지번(대표지번 외) | 1:N |
| 오수정화시설 | 건축물의 오수정화시설 | 1:N |
| 지역지구구역 | 총괄/동 단위 지역지구구역 | 1:N |
| 주택가격 | 공동주택 가격 정보 | 1:N |

- **상위 계층**: **총괄표제부 > 표제부 > 전유부** (문서: “건축물상위: 총괄표제부 > 표제부 > 전유부”).
- **토지 데이터**: 위 문서는 **건축물대장정보** 서비스만 다루며, **토지**(토지특성정보·토지대장 등) 테이블은 포함되지 않는다. 토지–건물 연결은 필지(PNU)·지번 단위로 이루어지며, RA 공공 데이터 소개 등 별도 자료를 참고해야 한다.

---

## 1.4 archhub_seongsu_20260127_152635 폴더와 PublicDataReader·연결관계 매핑

`collectors/data/raw/archhub/archhub_seongsu_20260127_152635` 폴더에는 **건축물대장(bldrgst)** 과 **건축인허가(archpms)** 수집 결과가 함께 들어 있다. PublicDataReader 문서의 “건축물대장 테이블 관계”와 직접 대응하는 것은 **건축물대장(bldrgst)** 쪽이다.

### 건축물대장(bldrgst) 파일 — PublicDataReader 대장 유형과 연결키

아래 파일들은 모두 **동일 건물**을 가리킬 때 **`mgmBldrgstPk`(관리건축물대장PK)** 로 연결된다. PublicDataReader의 “관리건축물대장PK로 테이블 연결”과 동일한 개념이다.

| ArchHub 파일명(오퍼레이션) | PublicDataReader 대장 유형 | 비고 |
|---------------------------|----------------------------|------|
| `bldrgst_getBrBasisOulnInfo_*` | 기본개요 | 대장 종류별 관리 |
| `bldrgst_getBrRecapTitleInfo_*` | 총괄표제부 | VWorld lt-c-spbd와 동일 계층 |
| `bldrgst_getBrTitleInfo_*` | 표제부 | 동 단위 |
| `bldrgst_getBrFlrOulnInfo_*` | 층별개요 | 1:N |
| `bldrgst_getBrAtchJibunInfo_*` | 부속지번 | 1:N, 본 문서 결합 대상 |
| `bldrgst_getBrExposPubuseAreaInfo_*` | 전유공용면적 | 1:N |
| `bldrgst_getBrWclfInfo_*` | 오수정화시설 | 1:N |
| `bldrgst_getBrHsprcInfo_*` | 주택가격 | 1:N |
| `bldrgst_getBrExposInfo_*` | 전유부 | 1:N |
| `bldrgst_getBrJijiguInfo_*` | 지역지구구역 | 1:N |

- **결합 시**: 기본개요·총괄표제부·표제부 중 하나를 기준으로 두고, 나머지 bldrgst 파일들을 **`mgmBldrgstPk`** 기준으로 조인하면, PublicDataReader ERD와 같은 “건물 1건–대장 유형별 N건” 구조를 재현할 수 있다.

### ArchHub 소스별 매칭 적합성 (성수동 수집 기준)

VWorld 건물(성수동 6,194 feature)과 결합할 때, 건물 수(레코드 수)와 매칭에 쓸 수 있는 필드가 다르다.

| 소스(오퍼레이션) | 대장 유형 | 성수동 수집 건수 | PNU(지번) | 도로12·본부번 | 도로명·본번 | 비고 |
|------------------|-----------|------------------|-----------|---------------|-------------|------|
| **getBrBasisOulnInfo** | 기본개요 | **33,361** | O | X (공백) | X (공백) | PNU만 매칭 가능, 건수 최다 |
| getBrRecapTitleInfo | 총괄표제부 | 245 | O | O 일부 | O 일부 | 건물당 1건, VWorld와 동일 계층 |
| getBrTitleInfo | 표제부 | 5,477 | O | X | X | 동 단위, PNU만 |
| getBrAtchJibunInfo | 부속지번 | 827 | O 대표+부속 | O | O | 부속지번 있는 건물만 |

- 매칭률을 높이려면: **기본개요(getBrBasisOulnInfo)** 를 소스로 쓰면 PNU 기준 건수가 33,361건이라 성수동 VWorld 6,194건 대비 PNU 매칭 가능 범위가 가장 넓다. 기본개요·표제부는 도로명/도로코드가 비어 있어 PNU 매칭만 사용 가능.
- 결합 스크립트: `--archhub-recap`(총괄표제부), `--archhub-basis`(기본개요), 부속지번(기본) 중 하나 선택.

### 건축인허가(archpms) 파일 — 건축물대장과의 관계

건축인허가는 **공급 예정·신축** 건물에 대한 정보로, PublicDataReader 건축물대장 문서에는 포함되지 않는다. 같은 폴더에 있는 archpms 파일은 아래와 같다.

| ArchHub 파일명(오퍼레이션) | 비고 |
|---------------------------|------|
| `archpms_getApBasisOulnInfo_*` | 건축인허가 기본개요 |
| `archpms_getApDongOulnInfo_*` | 동별개요 |
| `archpms_getApFlrOulnInfo_*` | 층별개요 |
| `archpms_getApHoOulnInfo_*` | 호별개요 |
| `archpms_getApImprprInfo_*` | 대수선 |
| `archpms_getApHdcrMgmRgstInfo_*` | 공작물관리대장 |
| `archpms_getApDemolExtngMgmRgstInfo_*` | 철거·멸실관리대장 |
| `archpms_getApTmpBldInfo_*` | 가설건축물 |
| `archpms_getApWclfInfo_*` | 오수정화시설 |
| `archpms_getApPklotInfo_*` | 주차장 |
| `archpms_getApAtchPklotInfo_*` | 부설주차장 |
| `archpms_getApExposPubuseAreaInfo_*` | 전유공용면적 |
| `archpms_getApHoExposPubuseAreaInfo_*` | 호별 전유공용면적 |
| `archpms_getApJijiguInfo_*` | 지역지구구역 |
| `archpms_getApRoadRgstInfo_*` | 도로명대장 |
| `archpms_getApPlatPlcInfo_*` | 대지위치 |
| `archpms_getApHsTpInfo_*` | 주택유형 |

- 인허가–완공 대장 연결은 **주소·대지위치·지번** 등으로 매칭하는 방식이 일반적이며, PublicDataReader 문서의 “건축물대장 테이블 관계” 범위 밖이다.

### 요약

- **PublicDataReader** 문서에는 **건축물대장** 10개 테이블의 **연결관계(ERD)** 와 **연결키(관리건축물대장PK)** 설명이 있다. **토지** 테이블은 해당 문서에 없고, 토지–건물 연결은 PNU·필지 단위 자료(RA 문서 등)로 보완한다.
- **archhub_seongsu_20260127_152635** 폴더의 **bldrgst** 파일 10개는 위 PublicDataReader 대장 유형과 1:1 대응하며, **`mgmBldrgstPk`** 로 서로 연결하면 된다. **archpms** 파일은 건축인허가 전용이며, 건축물대장 ERD와는 별도로 주소·지번 등으로 결합해야 한다.

---

## 2. 두 JSON 파일 구조 요약

### 2.1 VWorld `seongsu_lt-c-spbd_*.json`

- **형식**: GeoJSON FeatureCollection (또는 동일 구조의 `.json`).
- **레이어**: `LT_C_SPBD` — 건축물대장 총괄표제부 기반 건물 폴리곤.
- **Feature 예시**  
  - `geometry`: MultiPolygon (건물 footprint).  
  - `properties` 예:
    - `pk`, `bd_mgt_sn`: 건축물대장 쪽 식별자.
    - `sig_cd`: 시군구코드(5자리, 예: 11200=성동구, 11680=강남구).
    - `emd_cd`: 읍면동코드(3자리).
    - `pnu`: 필지고유번호(19자리 등).
    - `rd_nm`: 도로명, `bld_s`, `bld_e`, `buld_no`: 건물번호/본·부번.
    - `buld_nm`, `sido`, `sigungu`, `gu`: 건물명, 시도, 시군구, 동명.

성동구만 쓰는 경우 `sig_cd == "11200"` 로 필터링하면 ArchHub 수집 범위(성동구 성수동1가·2가)와 맞출 수 있다.

### 2.2 ArchHub `bldrgst_getBrAtchJibunInfo_*.json`

- **형식**: API 응답 형태의 JSON (`metadata`, `items`).
- **오퍼레이션**: 건축물대장 **부속지번 조회** (getBrAtchJibunInfo).
- **Item 예시**  
  - `mgmBldrgstPk`: 관리건축물대장 PK (건물 1건당 동일).  
  - `platPlc`: 대지위치(지번주소).  
  - `newPlatPlc`: 도로명주소 (예: `서울특별시 성동구 왕십리로14길 29 (성수동1가)`).  
  - `bldNm`: 건물명.  
  - `sigunguCd`, `bjdongCd`, `bun`, `ji`: 시군구·법정동·본번·부번.  
  - `naRoadCd`, `naMainBun`, `naSubBun`: 도로명코드, 도로명 본·부번.

ArchHub 데이터는 **좌표가 없고**, 주소·도로명·건물명·PK만 있으므로, VWorld 건물과 연결하려면 **주소/도로명 매칭** 또는 **PK·지번 정규화**가 필요하다.

---

## 3. 연결 키 후보와 전략

### 3.1 직접 PK 매칭의 한계

- VWorld `bd_mgt_sn`: 문자열 형태 (예: `1168011000104790000000002`).  
- ArchHub `mgmBldrgstPk`: 숫자형 (예: `1005117135`).  
- 두 값의 체계가 다르고, 현재 VWorld 레이어가 ArchHub와 동일한 PK 체계를 노출하지 않을 수 있어 **단순 동등 조인은 어렵다**.

### 3.2 권장: PNU 19자리 정확 매칭

- **PNU 형식**: 시군구(5) + 법정동(5) + 대지구분(1) + 본번(4) + 부번(4) = 19자리.  
- **VWorld**: `properties.pnu` 그대로 사용(19자리 정규화).  
- **ArchHub**: 대표지번 `sigunguCd`+`bjdongCd`+`platGbCd`+`bun`+`ji`, 부속지번 `atchSigunguCd`+`atchBjdongCd`+`atchPlatGbCd`+`atchBun`+`atchJi` 각각으로 PNU 19자리 생성 후 인덱스.  
- **대지구분 0/1**: VWorld와 ArchHub 간 11번째 자리(대지구분)가 0 vs 1로 다를 수 있어, 조회 시 두 variant 모두 사용하면 매칭 건수가 늘어난다.  
- **효과**: 같은 필지(PNU) 기준으로만 연결되므로 **오매칭이 없음**. 도로명+본번 “같은 도로 첫 건물” 부분 매칭은 제거하는 것이 좋다.

결합 스크립트는 **`--match-by pnu`**(기본값)로 PNU 매칭, **`--match-by addr`**로 도로명+본번 매칭을 선택할 수 있다.

### 3.3 도로명 + 건물번호(본번) 매칭 (보조)

- **VWorld**: `rd_nm`(도로명) + `bld_s` / `buld_no`(본번) → 키 `(도로명_정규화, 본번)`.  
- **ArchHub**: `newPlatPlc`에서 “도로명 + 본번” 추출 → 동일 키.  
- **주의**: “같은 도로, 다른 본번”인데 첫 번째 건물로 붙이는 **부분 매칭**은 오매칭을 유발하므로, 도로명+본번을 쓸 때는 **정확 (도로명, 본번) 일치만** 사용하는 것이 안전하다.

### 3.4 도로코드+건물번호 조합 비교 (sig_cd, rn_cd, bld_s, bld_e ↔ naRoadCd, naMainBun, naSubBun)

VWorld 건물 레이어의 **도로·건물번호** 필드와 ArchHub 부속지번의 **도로명코드·본·부번**을 조합으로 비교한 결과다.

| VWorld (GeoJSON properties) | ArchHub (items) | 비고 |
|-----------------------------|------------------|------|
| `sig_cd` | `naRoadCd` 앞 5자리 | 시군구코드(5자리) |
| `rn_cd` | `naRoadCd` 6~12자리(7자리) | 도로명코드(7자리) |
| `bld_s`, `bld_e` | `naMainBun`, `naSubBun` | 본번·부번 (VWorld는 범위/단일, ArchHub는 단일) |

- **도로 12자리**: `sig_cd`(5) + `rn_cd`(7자리 패딩) = 12자리로 만들면 ArchHub `naRoadCd`(12자리)와 **동일 체계**로 비교 가능하다.
- **비교 스크립트**: `collectors/scripts/compare_vworld_archhub_road_bld.py`  
  - 입력: VWorld GeoJSON, ArchHub `bldrgst_getBrAtchJibunInfo_*.json`  
  - (도로 12자리, 본번, 부번) 조합을 정규화한 뒤 양쪽 공통 집합·매칭 feature 수를 출력한다.

**성수동 전용 데이터 기준 실행 결과** (2026-02-01):

| 항목 | 값 |
|------|-----|
| VWorld feature 수 | 6,194 |
| VWorld unique (road_12, bld_s, bld_e) | 4,835 |
| VWorld unique 도로 12자리 | 157 |
| ArchHub unique (naRoadCd, naMainBun, naSubBun) | 391 |
| ArchHub unique naRoadCd | 113 |
| **도로 12자리 교집합** | **112** |
| **(도로+본번+부번) 키 일치 건수** | **389** |
| **해당 키를 가진 VWorld feature 수** | **599** |
| **feature 기준 매칭률** | **9.7%** (599/6194) |

- PNU 매칭(동일 성수동 데이터)은 **692건(11.2%)** 이므로, **도로+건물번호 조합만으로는 PNU보다 약간 적게 매칭**된다.
- 도로코드 체계는 호환되며(sig_cd+rn_cd = naRoadCd), 같은 도로·같은 본·부번인 경우에만 일치하므로 **오매칭 위험은 낮다**. 다만 부속지번 데이터에 해당 (도로, 본번, 부번)이 없으면 매칭되지 않는다.

#### 3.4.1 기본개요(기본개요)의 naRoadCd·naMainBun·naSubBun 활용 검토

기본개요(getBrBasisOulnInfo) JSON에도 **naRoadCd**, **naMainBun**, **naSubBun** 필드가 있으며, 성수동 수집본 기준 **일부만** 채워져 있다.

| 항목 | 값 |
|------|-----|
| 기본개요 items 총 건수 | 33,361 |
| naRoadCd 12자리 유효 건수 | 32,813 |
| unique (naRoadCd, naMainBun, naSubBun) 키 수 | 4,572 |
| VWorld unique (road_12, (main, sub)) 키 수 | 4,835 |
| **키 교집합** | **4,566** |
| **도로·건물번호만으로 매칭 가능한 VWorld feature 수** | **5,841** |

**키 매핑 (동일 체계)**

- **VWorld**: `sig_cd`(5) + `rn_cd`(7자리 패딩) → **road_12**; `bld_s`, `bld_e` → **(main, sub)** 정규화.
- **기본개요**: `naRoadCd`(12자리), `naMainBun`, `naSubBun` → **(road_12, (main, sub))**.
- 정규화 규칙을 맞추면(본·부번 앞 0 제거, 동일 키 형식) 양쪽을 **동일 연결키**로 결합 가능하다.

**PNU vs 도로·건물번호 (성수동 6,194 feature 기준)**

| 구분 | 건수 |
|------|------|
| PNU로만 매칭 | 5,967 |
| 도로·건물번호로만 매칭 가능 | 5,841 |
| PNU·도로·건물번호 둘 다 매칭 | 5,800 |
| **PNU 미매칭인데 도로·건물번호로만 매칭 가능** | **41** |
| PNU 매칭인데 도로·건물번호 없음(기본개요 해당 키 없음) | 167 |

**결론**

- 기본개요만 쓸 때 **캐스케이드(1단계 PNU → 2단계 도로12자리+본·부번)** 를 적용하면, PNU로 못 맞춘 **41건**을 2단계에서 추가로 매칭할 수 있다. (5,967 → **6,008**)
- 결합 스크립트는 현재 기본개요 + cascade 시 2단계 인덱스(`arch_by_road_bld`)를 비워 두고 있어, 이 41건이 반영되지 않는다. 기본개요 JSON이 총괄표제부와 동일하게 `naRoadCd`·`naMainBun`·`naSubBun` 필드를 갖추고 있으므로, **기본개요용 road_bld 인덱스를 채워 cascade 2단계를 활성화**하면 위 41건 추가 매칭을 구현할 수 있다. (3단계 도로명+본번은 기본개요에 `newPlatPlc`가 비어 있어 계속 미사용.)

### 3.5 1:N 처리

- 한 건물(VWorld 1 feature)에 부속지번이 여러 건(ArchHub items with same `mgmBldrgstPk`)인 경우:
  - **시각화/한 파일로 쓸 때**: VWorld feature 하나에 대표 1건만 붙이거나(예: 첫 번째 부속지번), `bldrgst_*` 필드를 하나의 객체로 넣고 나머지는 별도 테이블로 유지.
  - **정규화 유지**: 결합 스크립트는 “건물 1건당 대표 1건 매칭”으로 VWorld 속성만 확장하고, 상세 부속지번 목록은 ArchHub 원본을 FK(`mgmBldrgstPk`)로 참조하는 방식이 안전하다(문서 [활용및결합방안.md](./건축hub/활용및결합방안.md)의 “테이블 분리 + FK”와 동일).

### 3.6 100% 연결을 위한 공통필드 매칭 전략 (캐스케이드)

동일 건물 예: VWorld `성수일로8길 47` (성수동2가, 관리사무소·노인정·보육시설) ↔ ArchHub `newPlatPlc: 성수일로8길 47 (성수동2가)`, `bldNm: 관리사무소,노인정,보육시설`.

**공통 필드 매핑 (검증된 1:1 대응)**

| 공통 개념 | VWorld (GeoJSON properties) | ArchHub (items) | 정규화·비고 |
|-----------|-----------------------------|------------------|-------------|
| 시군구코드 | `sig_cd` (5자리) | `sigunguCd`, `naRoadCd` 앞 5자리 | "11200" |
| 법정동(동코드) | `emd_cd` (3자리) | `bjdongCd` (5자리, 하위 3자리 114/115) | 성수동1가=114, 성수동2가=115 |
| 도로 12자리 | `sig_cd` + `rn_cd` (7자리 패딩) | `naRoadCd` (12자리) | 동일 체계 |
| 본번·부번 | `bld_s`, `bld_e` | `naMainBun`, `naSubBun` | 단일일 때 (bld_s, bld_e) = (naMainBun, naSubBun) |
| PNU 19자리 | `pnu` | 대표/부속지번으로 생성 (대지구분 0/1 variant) | §3.2 |
| 도로명(문자) | `rd_nm` | `newPlatPlc` 내 도로명 파싱 | 공백·특수문자 제거 정규화 |
| 건물명 | `buld_nm` | `bldNm` | 보조·타이 브레이크용 |

**100% 연결을 위한 단계별(캐스케이드) 전략**

- **원칙**: 한 VWorld feature당 **한 번만** 매칭 확정. 먼저 성공한 단계에서 확정하고 이후 단계는 건너뜀.
- **ArchHub 측**: 동일 `(naRoadCd, naMainBun, naSubBun)` 또는 동일 `mgmBldrgstPk`에 여러 item(부속지번)이 있을 수 있으므로, 매칭 시 **mgmBldrgstPk 기준 대표 1건**만 붙이거나, 첫 번째 item의 필드를 사용.

| 단계 | 키 | VWorld → ArchHub 조회 | 신뢰도 | 비고 |
|------|-----|------------------------|--------|------|
| **1** | PNU 19자리 (대지구분 0/1 variant) | `pnu` 정규화 후 인덱스 조회 | 최고 | §3.2, 오매칭 없음 |
| **2** | 도로 12자리 + 본번 + 부번 | `(sig_cd+rn_cd, bld_s, bld_e)` 정규화 = `(naRoadCd, naMainBun, naSubBun)` | 높음 | §3.4, 코드 체계 동일 |
| **3** | 도로명(문자) + 본번 | `(rd_nm 정규화, bld_s 또는 buld_no 본번)` = `newPlatPlc` 파싱 (도로명, 본번) | 중간 | §3.3, 동일 법정동(emd_cd/bjdongCd) 필터 권장 |
| **4** | (선택) 건물명 보조 | `buld_nm` ↔ `bldNm` | 보조 | 동일 (도로, 본번) 다건일 때만 타이 브레이크 |

**구현 시 유의**

1. **1단계**에서 매칭된 feature는 2·3·4단계 대상에서 제외.
2. **2단계**: 본·부번은 문자열 정규화 통일(앞 0 제거 또는 숫자 비교). VWorld `bld_e`가 "0"이면 부번 없음 = ArchHub `naSubBun` "0".
3. **3단계**: `newPlatPlc` 파싱 시 "서울특별시 성동구 … (성수동…)" 패턴으로 도로명·본번 추출. 동일 (도로명, 본번)이 여러 ArchHub 건물에 있으면 `emd_cd`(또는 gu)와 `bjdongCd`로 좁히기.
4. **4단계**: 건물명은 포함 관계 또는 유사도로만 사용하고, 단독 키로 쓰지 않음(오매칭 위험).

**매칭률 기대**

- 1단계(PNU): 현재 약 11.2% (ArchHub에 해당 PNU가 있는 경우만).
- 1+2단계: PNU 미매칭 feature 중 (도로 12자리, 본·부번) 일치 추가 → 약 9.7% feature가 2단계로 매칭 가능(중복 제거 후 1단계와 합치면 더 많은 고유 건물 연결).
- 1+2+3단계: 도로명+본번 fallback으로 추가 매칭 가능. 3단계는 동일 법정동 제한 시 오매칭을 줄일 수 있음.

**정리**: "100% 연결"은 ArchHub에 해당 건물 레코드가 존재하는 범위 내에서만 가능하다. 부속지번 API는 부속지번이 있는 건물만 포함하므로, **PNU(1단계) + 도로12·본부번(2단계) + 도로명·본번(3단계)** 캐스케이드로 최대한 매칭하고, 남는 VWorld feature는 ArchHub에 대장 정보가 없는 건물로 보는 것이 안전하다.

### 3.7 기본개요(기본개요) 매칭 방식

**기본개요**(getBrBasisOulnInfo)는 건축물대장의 **대장 종류별 관리** 정보로, 성수동 수집 시 **33,361건**으로 다른 소스(총괄표제부 245건, 부속지번 827건)보다 훨씬 많다. 대신 `naRoadCd`, `newPlatPlc` 등 도로명·도로코드 필드가 **공백**이어서 **PNU(지번)만** 매칭에 사용한다.

**1. ArchHub 쪽 인덱스 구성**

- **입력**: `bldrgst_getBrBasisOulnInfo_*.json` (items 배열).
- **PNU 19자리 생성**: 각 item에서 `sigunguCd`(5) + `bjdongCd`(5) + `platGbCd`(1) + `bun`(4) + `ji`(4) → 19자리 문자열.
- **대지구분 0/1 variant**: VWorld와 ArchHub 간 11번째 자리(대지구분)가 0 vs 1로 다를 수 있으므로, 각 PNU에 대해 **0↔1 바꾼 variant**도 인덱스에 넣어 둠.
- **결과**: `{ pnu_19: item, ... }` 형태의 PNU 인덱스(약 9,626키 = 33,361건 × variant 반영 후 중복 제거).

**2. VWorld 쪽 조회**

- 각 VWorld feature의 `properties.pnu`를 **19자리로 정규화**.
- 정규화한 PNU로 ArchHub 인덱스 조회; 없으면 **대지구분 0/1 바꾼 PNU**로 한 번 더 조회.
- 조회 성공 시 해당 item 전체를 `bldrgst_*` 접두어로 properties에 붙이고, `bldrgst_matched = true`, `bldrgst_match_source = "pnu"` 설정.

**3. 캐스케이드에서의 역할**

- `--archhub-basis --match-by cascade` 로 실행하면 **1단계(PNU)만** 유효하다.
- 2단계(도로 12자리+본·부번), 3단계(도로명+본번)는 기본개요에 도로/주소 필드가 없어 **비어 있는 인덱스**로 두고, 매칭 건수 0.

**4. 실행 결과 (성수동 기준)**

- VWorld feature 6,194건 중 **5,967건 매칭** (약 96.3%).
- `matched_pnu: 5967`, `matched_road_bld: 0`, `matched_addr: 0`.
- 기본개요 건수(33,361)가 VWorld 성수동 건수(6,194)보다 많아, PNU만으로도 **매칭률이 가장 높음**.

**5. 실행 예**

```bash
python collectors/scripts/combine_archhub_vworld_building_register.py --archhub-basis --match-by cascade --out-dir collectors/data/raw/combined/vworld_seongsu_bldrgst_basis_20260127
```

### 3.8 100% 매칭을 위한 방안

기본개요만으로는 성수동 6,194건 중 5,967건(96.3%)만 매칭되고, **약 227건이 비매칭**이다. 100%에 가깝게 하기 위한 방안과 한계를 정리한다.

**1. 현실적 상한**

- **건축물대장에 없는 건물**은 어떤 소스로도 매칭할 수 없다.
  - VWorld에만 있는 시설(공원 관리동, 미등기 건물, 철거·멸실 후 공간 등), 건축물대장 수집 범위 밖 지역 등.
- 따라서 **“VWorld 성수동 전체” 기준 100%**는, ArchHub에 해당 건물 레코드가 전부 있다는 전제가 성립할 때만 이론상 가능하다.

**2. 다소스 활용 시 유의**

- **1단계**: 기본개요(기본개요)로 PNU 매칭 → 5,967건 매칭.
- **2단계**: 매칭 안 된 227건만 대상으로, 총괄표제부 또는 부속지번으로 도로 12자리+본·부번, 도로명+본번 순으로 추가 매칭하려면, 결합 스크립트는 **단일 소스만** 선택하므로 **기본개요 실행 후 미매칭 feature만 추려서 총괄표제부/부속지번으로 재실행**하는 **2회 실행** 또는 스크립트 확장이 필요하다.
- **일관성**: 다소스 결과는 feature별로 붙는 `bldrgst_*` 컬럼이 소스마다 달라져 **스키마·필드 구성이 feature마다 다르므로**, 한 번에 다소스 캐스케이드를 실행하는 방식은 제공하지 않는다. 2회 실행 시에는 출력을 각각 두 GeoJSON으로 두거나, 동일 소스만 묶어서 사용하는 것이 안전하다.

**3. 비매칭 원인 분석**

- 227건에 대해 다음을 확인하면 원인 파악에 도움이 된다.
  - VWorld `pnu`가 19자리인지, 앞자리 0 누락 등 **정규화 후에도 유효한지**.
  - 해당 PNU(및 대지구분 0/1 variant)가 **기본개요 JSON에 실제로 존재하는지**.
  - `sig_cd`, `emd_cd`, `rd_nm`, `bld_s`, `bld_e` 등으로 **총괄표제부/부속지번에는 있는지** 검색.
- 분석 결과, “ArchHub 어느 소스에도 없음”이면 해당 feature는 **현재 데이터로는 매칭 불가**로 보는 것이 맞다.

**4. 완화 매칭(주의)**

- **대지구분(11번째 자리) 무시**: PNU 19자리 중 11번째만 0/1로 바꿔 보는 것은 이미 적용되어 있음. 그 외 자리까지 완화하면 **서로 다른 필지가 같은 키로 묶일 위험**이 있어 비권장.
- **법정동+본번+부번만 매칭**: PNU 없이 시군구+법정동+본번+부번만 쓰면, 동일 본·부번이 다른 동에 있을 때 **오매칭** 가능성이 있음. 같은 법정동으로 한정해 보조용으로만 쓰는 것은 가능.

**5. 정리**

| 방안 | 내용 | 기대 효과 |
|------|------|-----------|
| **단일 소스(기본개요)** | `--archhub-basis --match-by cascade` 로 PNU 매칭 | 6,194건 중 약 5,967건(96.3%) 매칭, 스키마 일관 |
| **2회 실행** | 기본개요 실행 후 미매칭만 총괄표제부/부속지번으로 재실행 | 227건 중 일부 추가 매칭 가능(출력은 소스별로 분리 권장) |
| **비매칭 샘플 분석** | 227건의 pnu·주소·ArchHub 존재 여부 확인 | 매칭 불가 구간·데이터 품질 파악 |
| **추가 수집** | 표제부(5,477건) 등 다른 대장으로 PNU 보강 | 이론상 PNU 커버리지 확대 가능 |

- **100%**는 “ArchHub에 레코드가 있는 건물만” 범위에서만 의미가 있으며, 그 범위 안에서도 **기본개요 단일 소스 + 비매칭 분석**(및 필요 시 2회 실행)으로 최대한 끌어올리는 것이 현실적인 방안이다.

---

## 4. 결합 절차 요약

1. **VWorld GeoJSON 로드**  
   - `seongsu_lt-c-spbd_20260127_134933.json` 의 `features` 사용.  
   - 성동구만 쓸 경우 `properties.sig_cd == "11200"` 필터.

2. **ArchHub JSON 로드**  
   - **PNU 매칭**(`--match-by pnu`, 기본): 대표지번·부속지번 각각 PNU 19자리 생성, 대지구분 0/1 variant 포함해 인덱스.  
   - **도로명+본번 매칭**(`--match-by addr`): `mgmBldrgstPk` 기준 중복 제거 후, `newPlatPlc`에서 `(도로명_정규화, 본번)` 추출해 인덱스.

3. **매칭**  
   - **PNU**: 각 VWorld feature의 `pnu`를 19자리 정규화 후 ArchHub PNU 인덱스에서 조회(대지구분 0/1 variant 둘 다 시도).  
   - **addr**: 각 VWorld feature의 `(rd_nm 정규화, 본번)`으로 ArchHub 인덱스 조회(정확 일치만).  
   - 매칭되면 해당 건축물대장(부속지번) 필드를 `bldrgst_*` 접두어로 properties에 추가.

4. **산출**  
   - 결합된 FeatureCollection을 GeoJSON으로 저장 (예: `seongsu_building_register_combined.geojson`).  
   - 매칭 통계는 `combine_summary.json` 등으로 남기면 재현·검증에 유리하다.

자동화된 실행 방법은 아래 “기존 스크립트 사용”을 참고하면 된다.

---

## 5. 기존 스크립트 사용

프로젝트에 이미 **VWorld 건물 + ArchHub 부속지번** 결합 스크립트가 있다.

- **스크립트**: `collectors/scripts/combine_archhub_vworld_building_register.py`  
- **전제**:  
  - VWorld: `lt-c-spbd` GeoJSON(또는 동일 구조의 `.json`).  
  - ArchHub: `bldrgst_getBrAtchJibunInfo` JSON.  
- **동작**:  
  - ArchHub를 `newPlatPlc` 기준으로 (도로명, 본번) 인덱스.  
  - VWorld는 `rd_nm`, `bld_s`/`buld_no`로 동일 키 생성 후 매칭.  
  - 매칭된 건물에만 `bldrgst_*` 속성 부여.  
- **실행 예** (프로젝트 루트가 `framework`일 때):

```bash
# 기본: PNU 매칭(--match-by pnu), 최신 폴더 사용
python collectors/scripts/combine_archhub_vworld_building_register.py

# PNU 매칭 + 파일·출력 폴더 지정
python collectors/scripts/combine_archhub_vworld_building_register.py ^
  --archhub "collectors/data/raw/archhub/archhub_seongsu_20260127_152635/bldrgst_getBrAtchJibunInfo_11200_seongsu_20260127_152635.json" ^
  --vworld "collectors/data/raw/vworld/vworld_seongsu_20260127_134933/seongsu_lt-c-spbd_20260127_134933.geojson" ^
  --out-dir "collectors/data/raw/combined/vworld_seongsu_bldrgst_pnu_20260127" ^
  --match-by pnu

# 도로명+본번 정확 매칭만 (과거 방식, 부분 매칭 제거)
python collectors/scripts/combine_archhub_vworld_building_register.py ... --match-by addr
```

PowerShell에서는 `^` 대신 백슬래시 줄 continuation 또는 한 줄로 나열하면 된다.

- **출력**:  
  - 지정한 `--out-dir` 아래 `seongsu_building_register_combined.geojson`, `combine_summary.json`.

VWorld 파일이 `.geojson`이 아니라 `.json`이어도 내용이 GeoJSON FeatureCollection이면 같은 스크립트로 처리 가능하다. 단, 스크립트 기본값이 `.geojson`을 찾도록 되어 있으므로, 사용 시 `--vworld`로 위 `.json` 경로를 넘겨주는 것이 좋다.

---

## 6. PublicDataReader와 VWorld JSON 연동·활용

[PublicDataReader](https://github.com/WooilJeong/PublicDataReader)는 **공공 데이터 조회를 위한 오픈소스 파이썬 라이브러리**이다. 공공데이터포털·국가통계포털(KOSIS)·V-World 등 오픈 API 서비스를 통일된 방식으로 조회할 수 있으며, `pip install PublicDataReader --upgrade`로 설치한다. 아래는 **이미 수집된 VWorld 건물 레이어** `collectors/data/raw/vworld/vworld_seongsu_20260127_134933/seongsu_lt-c-spbd_20260127_134933.json` 과 PublicDataReader를 연결해 활용하는 방안을 정리한 것이다.

### 6.1 연결 포인트 (VWorld JSON ↔ PublicDataReader)

VWorld `seongsu_lt-c-spbd_*.json` 의 각 feature `properties` 에는 PublicDataReader API 입력으로 바로 쓸 수 있는 항목이 있다.

| VWorld properties 예시 | PublicDataReader 활용 |
|------------------------|------------------------|
| `sig_cd` (시군구코드 5자리) | 건축물대장·건축인허가·법정동코드 조회 시 **sigungu_code** |
| `emd_cd` (읍면동코드 3자리) | 법정동코드 조회 시 읍면동 코드; 건축물대장은 **5자리 법정동코드** 사용 시 `sig_cd`+`emd_cd` 조합으로 변환 |
| `pnu` (필지고유번호) | 토지임야·토지소유·실거래 등 **PNU/필지 기준** 조인 |
| `rd_nm`, `bld_s`, `buld_no` (도로명, 본번, 건물번호) | 건축물대장·실거래·상가 **주소/도로명+본번** 매칭, 지오코딩 보조 |
| `bld_s`, `bld_e` (본번·부번) | 건축물대장 조회 시 **bun**, **ji** (선택) |

즉, VWorld JSON을 **기준 레이어**로 두고, PublicDataReader로 **공공데이터포털·V-World API**를 호출해 속성을 보강하거나 별도 레이어를 만든 뒤 결합할 수 있다.

### 6.2 활용 방안

#### (1) 건축물대장 API로 VWorld 건물 속성 보강

- **대상**: [PublicDataReader 건축물대장정보 사용 가이드](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/BuildingLedger.md) — 공공데이터포털 **건축물대장** (총괄표제부, 표제부, 부속지번, 층별개요 등).
- **연결**: VWorld feature별로 `sig_cd` → 시군구코드, `emd_cd` → 법정동코드(5자리), `bld_s`/`bld_e` → bun/ji 로 넣어 `BuildingLedger(service_key).get_data(ledger_type="총괄표제부", sigungu_code=..., bdong_code=..., bun=..., ji=...)` 를 호출.
- **활용**: 기존 ArchHub 부속지번 JSON 없이도 **실시간·온디맨드**로 건축물대장 정보를 가져와 VWorld feature에 붙일 수 있다. 대량 호출 시 API 할당량·지연을 고려해, 샘플 구역(예: 성동구 성수동)이나 일부 건물만 먼저 적용하는 방식을 권장한다.

#### (2) 법정동·행정동 코드 매핑 (라벨·필터·검증)

- **대상**: PublicDataReader **법정동코드·행정동코드 조회** ([정우일 블로그 - 법정동코드와 행정동코드 조회하기](https://wooiljeong.github.io/python/pdr-code/)).
- **연결**: VWorld의 `sig_cd`, `emd_cd`(또는 법정동코드 10자리)와 매핑해 **시군구명·읍면동명** 등을 얻는다.
- **활용**: 지도 라벨, 시군구/동 필터, 주소 정규화·검증, 성동구(11200) 등 특정 구만 추출할 때 유용하다.

#### (3) V-World API로 동일 지역·추가 레이어 수집

- **대상**: PublicDataReader **국가공간정보 사용 가이드** ([VworldData.md](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/vworld/VworldData.md)) — V-World(공간정보 오픈플랫폼) API.
- **연결**: 이미 보유한 `seongsu_lt-c-spbd_*.json` 은 **lt-c-spbd(건물 총괄표제부)** 레이어의 스냅샷이다. PublicDataReader VworldData로 **동일 bbox·동일/다른 레이어**를 조회해 최신 스냅샷을 만들거나, **토지·건물 외 레이어**를 추가로 수집할 수 있다.
- **활용**: 수집 시점이 다른 데이터 비교, 토지 폴리곤 등 다른 레이어와 공간 조인 후 VWorld 건물 레이어에 PNU·지번 등 토지 속성을 붙이는 데 사용할 수 있다.

#### (4) 토지임야·토지소유와 PNU 기준 결합

- **대상**: [국토교통부 토지임야정보](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/LandForestLedger.md), [토지소유정보](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/LandOwnership.md).
- **연결**: VWorld feature의 `pnu`(필지고유번호)로 토지대장·소유정보를 조회하거나 조인한다.
- **활용**: 건물이 올라간 필지의 토지 용도·면적·소유자 등을 VWorld 건물 레이어에 붙여 분석·시각화할 수 있다.

#### (5) 실거래가·상가 정보와 주소/지역 기준 결합

- **대상**: [국토교통부 부동산 실거래가](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/TransactionPrice.md), [소상공인 상가(상권)정보](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/SmallShop.md).
- **연결**: VWorld의 `sig_cd`·법정동코드·`rd_nm`+`bld_s` 등으로 지역/주소를 정규화한 뒤, 실거래·상가 API로 해당 구역·주소 데이터를 조회하고, 도로명+본번 또는 지오코딩으로 VWorld feature와 매칭한다.
- **활용**: 건물 폴리곤 위에 실거래 건수·평균가, 상가 수 등을 시각화하거나, 건물별 대표 실거래/상가 정보를 속성으로 붙일 수 있다.

### 6.3 사용 시 유의사항

- **인증키**: 건축물대장·토지·실거래·상가·V-World 등 대부분 **공공데이터포털(또는 해당 포털) 서비스키**가 필요하다. [공공데이터포털](https://www.data.go.kr/)에서 서비스별로 신청 후 `service_key` 변수에 넣어 사용한다.
- **호출 제한**: API당 일일·회당 호출 한도가 있으므로, VWorld 전체 feature를 한꺼번에 보강하기보다는 **구역·샘플 단위** 또는 **캐시·배치**로 처리하는 것이 안전하다.
- **코드 체계**: VWorld `emd_cd`는 3자리 등 단축된 값일 수 있다. PublicDataReader 건축물대장은 **5자리 법정동코드**(예: 11000)를 쓰므로, 행정표준코드·법정동코드 목록으로 변환 규칙을 맞춰야 한다.

### 6.4 참고 링크 (PublicDataReader)

| 자료 | URL | 비고 |
|------|-----|------|
| PublicDataReader 저장소 | https://github.com/WooilJeong/PublicDataReader | 설치·가이드 목록·이슈 |
| 건축물대장정보 사용 가이드 | [BuildingLedger.md](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/BuildingLedger.md) | 총괄표제부·표제부·부속지번 등 |
| 건축인허가정보 사용 가이드 | [BuildingLicense.md](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/BuildingLicense.md) | 공급 예정·인허가 건물 |
| 국가공간정보(V-World) 사용 가이드 | [VworldData.md](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/vworld/VworldData.md) | V-World 레이어 조회 |
| 토지임야정보 사용 가이드 | [LandForestLedger.md](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/LandForestLedger.md) | 토지대장·임야대장 |
| 토지소유정보 사용 가이드 | [LandOwnership.md](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/LandOwnership.md) | 토지 소유자 |
| 부동산 실거래가 사용 가이드 | [TransactionPrice.md](https://github.com/WooilJeong/PublicDataReader/blob/main/assets/docs/portal/TransactionPrice.md) | 실거래가 |
| 법정동코드·행정동코드 조회 | [정우일 블로그 pdr-code](https://wooiljeong.github.io/python/pdr-code/) | 시군구/법정동 코드 |

---

## 7. 참고 문서

| 문서 | 설명 |
|------|------|
| [건축hub 활용및결합방안.md](./건축hub/활용및결합방안.md) | 건축물대장 1:N 관계, VWorld–대장 결합 키·전략, 시각화 |
| [건축hub 수집체계_요약.md](./건축hub/수집체계_요약.md) | 건축물대장·건축인허가 오퍼레이션 목록, 시군구/법정동코드 |
| [RA 공공 데이터 소개](https://help.analytics.rsquareon.com/ko/articles/%EA%B3%B5%EA%B3%B5-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EC%86%8C%EA%B0%9C-36534bf4) | 필지·PNU 기반 공공데이터, 토지특성정보·건축물대장 |
| [PublicDataReader (GitHub)](https://github.com/WooilJeong/PublicDataReader) | 공공 데이터 조회 오픈소스 파이썬 라이브러리, 건축물대장·V-World·토지·실거래·상가 등 가이드 목록 |
| [PublicDataReader 건축물대장](https://wooiljeong.github.io/python/public_data_reader_03/) | 건축물대장 API 구조, **테이블관계도(ERD)**, 시군구/법정동코드, 총괄표제부·표제부·부속지번 등 10종, 연결키(관리건축물대장PK) |
| [PublicDataReader 테이블관계도 이미지](https://wooiljeong.github.io/assets/img/common/building_talbe_erd.png) | 건축물대장 테이블 ERD (building_talbe_erd.png) |
| `collectors/scripts/combine_archhub_vworld_building_register.py` | 도로명+본번 매칭 결합 스크립트 |

---

## 8. 요약

- **VWorld** `seongsu_lt-c-spbd_*.json`: 건축물대장 총괄표제부 기반 **건물 폴리곤**(공간).  
- **ArchHub** `bldrgst_getBrAtchJibunInfo_*.json`: 같은 건축물대장 체계의 **부속지번** 속성(무좌표).  
- **연결**: **PNU 19자리 정확 매칭**(`--match-by pnu`, 기본)을 권장한다. 대표지번·부속지번 각각 PNU 생성, 대지구분 0/1 variant로 조회 시 오매칭 없이 같은 필지만 연결된다. 도로명+본번(`--match-by addr`)은 정확 (도로명, 본번) 일치만 사용하는 것이 안전하다.  
- **PublicDataReader** 문서에는 건축물대장 **10종 테이블의 연결관계(ERD)** 와 **연결키(관리건축물대장PK)** 가 정리되어 있으며, **archhub_seongsu_20260127_152635** 폴더의 bldrgst 10개 파일은 이와 1:1 대응·**mgmBldrgstPk**로 서로 연결할 수 있다. 토지 테이블은 해당 문서에 없고, 토지–건물 연결은 PNU·필지 단위 자료로 보완한다.  
- **PublicDataReader**와 VWorld JSON(`seongsu_lt-c-spbd_*.json`) 연동: VWorld의 `sig_cd`·`emd_cd`·`pnu`·`rd_nm`·`bld_s` 등을 PublicDataReader의 건축물대장·법정동코드·V-World·토지·실거래·상가 API 입력으로 사용해 **속성 보강·추가 레이어·PNU/주소 기준 결합**이 가능하다. 상세는 본문 **6. PublicDataReader와 VWorld JSON 연동·활용** 참고.  
- 공공데이터 관점(필지·PNU·건축물대장 구조)은 참고 URL을 통해 정리했고, 실제 결합은 **도로명+본번 매칭**과 **필요 시 sig_cd(11200) 필터**로 수행하면 된다.
