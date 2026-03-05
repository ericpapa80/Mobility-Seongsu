# SGIS 스크립트 모음

SGIS(통계지리정보서비스) 관련 스크립트들을 기능별로 분류하여 정리한 폴더입니다.

## 폴더 구조

```
scripts/sgis/
├── collection/          # 데이터 수집 스크립트
├── theme_cd/           # 테마 코드 관련 스크립트
├── industry_mapping/   # 업종 코드 매핑 스크립트
├── coordinates/        # 좌표 관련 스크립트
└── utils/              # 기타 유틸리티 스크립트
```

## 스크립트 목록

### 📥 collection/ - 데이터 수집 스크립트
- **`run_sgis.py`**: SGIS 기술업종 통계지도 데이터 수집 스크립트
- **`run_sgis_timeseries.py`**: 연도별 시계열 데이터 수집 스크립트 (2016-2023)

### 🏷️ theme_cd/ - 테마 코드 관련 스크립트
- **`analyze_theme_cd.py`**: 테마 코드 분석
- **`extract_theme_cd_from_pdf.py`**: PDF에서 테마 코드 추출
- **`extract_theme_code_table.py`**: 테마 코드 테이블 추출
- **`extract_technical_biz_theme_cd.py`**: 기술업종 테마 코드 추출
- **`find_poi_theme_cd.py`**: POI 테마 코드 찾기
- **`test_theme_cd.py`**: 테마 코드 테스트

### 🔗 industry_mapping/ - 업종 코드 매핑 스크립트
- **`compare_theme_industry.py`**: 테마 코드와 업종 코드 비교
- **`compare_theme_industry_names.py`**: 테마 코드명과 업종 코드명 비교
- **`generate_theme_industry_mapping_csv.py`**: 테마 코드-업종 코드 매핑 CSV 생성
- **`analyze_theme_industry_mapping.py`**: 테마 코드-업종 코드 매핑 분석

### 📍 coordinates/ - 좌표 관련 스크립트
- **`analyze_coordinates.py`**: 좌표 분석
- **`check_sgis_coordinate_system.py`**: SGIS 좌표계 확인
- **`test_coordinate_systems.py`**: 다양한 좌표계 테스트
- **`convert_coordinates_5179_to_4326.py`**: EPSG:5179 → EPSG:4326 좌표 변환

### 🛠️ utils/ - 기타 유틸리티 스크립트
- **`find_seongdong_code.py`**: 성동구 행정구역 코드 찾기
- **`test_adm_codes.py`**: 행정구역 코드 테스트
- **`test_years_availability.py`**: 연도별 데이터 수집 가능 여부 테스트

## 사용 방법

### 데이터 수집

```bash
# 기본 수집
python scripts/sgis/collection/run_sgis.py

# 연도별 시계열 수집 (2016-2023)
python scripts/sgis/collection/run_sgis_timeseries.py
```

### 좌표 변환

```bash
# 좌표계 확인
python scripts/sgis/coordinates/check_sgis_coordinate_system.py

# 좌표 변환 (EPSG:5179 → EPSG:4326)
python scripts/sgis/coordinates/convert_coordinates_5179_to_4326.py
```

### 테마 코드 분석

```bash
# 테마 코드 분석
python scripts/sgis/theme_cd/analyze_theme_cd.py

# 업종 코드 매핑 CSV 생성
python scripts/sgis/industry_mapping/generate_theme_industry_mapping_csv.py
```

## 참고

- 모든 스크립트는 프로젝트 루트에서 실행해야 합니다.
- 상대 경로는 프로젝트 루트 기준으로 설정되어 있습니다.
- SGIS 관련 문서는 `docs/sources/sgis/` 폴더에 있습니다.

