# QGIS에서 VWorld CSV 파일 불러오기 가이드

## 개요

VWorld에서 수집한 CSV 파일의 WKT 컬럼을 QGIS에서 읽는 방법을 안내합니다.

## 파일 정보

- **파일 경로**: `collectors/data/raw/vworld/vworld_seongsu_YYYYMMDD_HHMMSS/seongsu_lt-c-landinfobasemap_YYYYMMDD_HHMMSS.csv`
- **좌표계**: EPSG:3857 (Web Mercator)
- **지오메트리 형식**: MULTIPOLYGON (WKT)
- **WKT 컬럼명**: `wkt`

## QGIS에서 불러오기

### 방법 1: 구분된 텍스트 레이어 추가 (권장)

1. **레이어 메뉴** → **레이어 추가** → **구분된 텍스트 레이어 추가**
   - 또는 툴바의 `텍스트 파일 추가` 아이콘 클릭

2. **파일 선택**
   - `파일명`에서 CSV 파일 선택
   - 예: `seongsu_lt-c-landinfobasemap_20260127_105315.csv`

3. **형식 설정**
   - **파일 형식**: `CSV (쉼표로 구분)`
   - **인코딩**: `UTF-8` (한글 포함 시)
   - **첫 번째 행에 필드명 사용**: ✅ 체크

4. **지오메트리 정의**
   - **지오메트리 정의**: `WKT` 선택
   - **WKT 필드**: `wkt` 선택

5. **좌표계 설정** ⚠️ **중요**
   - **좌표계**: `EPSG:3857 - WGS 84 / Pseudo-Mercator` 선택
   - 또는 검색창에 `3857` 입력하여 선택
   - **주의**: 좌표계를 올바르게 설정하지 않으면 지도에 올바르게 표시되지 않습니다.

6. **확인** 클릭하여 레이어 추가

### 방법 2: 드래그 앤 드롭

1. QGIS 메인 창에 CSV 파일을 드래그 앤 드롭
2. 자동으로 "구분된 텍스트 레이어 추가" 대화상자가 열림
3. 위의 3-6단계를 따라 설정

## 좌표계 확인 및 변환

### 현재 좌표계 확인

- **좌표계**: EPSG:3857 (Web Mercator)
- **X 좌표 범위**: 약 14,100,000 ~ 14,200,000
- **Y 좌표 범위**: 약 4,500,000 ~ 4,600,000

### 다른 좌표계로 변환하기

WGS84 (EPSG:4326)로 변환하려면:

1. 레이어를 마우스 오른쪽 클릭
2. **내보내기** → **다른 이름으로 저장**
3. **형식**: 원하는 형식 선택 (예: GeoPackage, Shapefile)
4. **좌표계**: `EPSG:4326 - WGS 84` 선택
5. 저장

또는:

1. 레이어를 마우스 오른쪽 클릭
2. **레이어 CRS 설정** → **레이어 CRS 설정**
3. 원하는 좌표계 선택

## 문제 해결

### 지오메트리가 표시되지 않는 경우

1. **좌표계 확인**
   - 레이어 속성 → 정보 → 좌표계가 EPSG:3857인지 확인
   - 잘못된 경우 "레이어 CRS 설정"에서 수정

2. **WKT 형식 확인**
   - CSV 파일의 WKT 컬럼이 올바른 형식인지 확인
   - 예: `MULTIPOLYGON((x1 y1, x2 y2, ...))`

3. **인코딩 확인**
   - 한글이 깨지는 경우 UTF-8 인코딩으로 다시 저장

### 좌표가 잘못된 위치에 표시되는 경우

- 좌표계가 잘못 설정되었을 가능성이 높습니다
- EPSG:3857로 올바르게 설정했는지 확인
- 레이어를 제거하고 다시 불러올 때 좌표계를 올바르게 설정

### 성능 문제

- 파일이 큰 경우 (25,000개 이상 피처)
- QGIS가 느려질 수 있음
- 필요시 필터링하거나 샘플 데이터로 테스트

## 참고 자료

- [QGIS 공식 문서 - CSV 파일 불러오기](https://docs.qgis.org/latest/ko/docs/user_manual/managing_data_source/opening_data.html#delimited-text-files)
- EPSG:3857: Web Mercator (Google Maps, OpenStreetMap 등에서 사용)
- EPSG:4326: WGS84 (위경도 좌표계)

## 관련 파일

- `collectors/scripts/vworld/collect_seongsu.py`: 데이터 수집 스크립트
- `collectors/scripts/vworld/add_coordinates_to_csv.py`: 좌표 추가 스크립트
