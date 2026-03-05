# SGIS 좌표계 정보

## 좌표계 확인 결과

SGIS 기술업종 통계지도 API에서 반환하는 `x`, `y` 좌표는 **EPSG:5179 (Korea 2000 / Central Belt 2010)** 좌표계를 사용합니다.

## 좌표 분석 결과

### 샘플 데이터
- **파일**: `data/raw/sgis/20251130_214212/sgis_technical_biz_20251130_214212.json`
- **총 항목 수**: 10,123개
- **지역**: 서울특별시 성동구

### 좌표 범위
- **x 좌표**: 956,674 ~ 962,302
- **y 좌표**: 1,948,455 ~ 1,952,572
- **x 평균**: 960,114.77
- **y 평균**: 1,950,067.45

### 좌표계 확인 방법

#### 1. 역변환 테스트
현재 좌표 값(x=959822, y=1950099)을 EPSG:5179로 가정하고 WGS84로 변환:
- **결과**: 경도 127.045148, 위도 37.549354
- **확인**: ✅ 서울 지역 좌표 (서울: 경도 126~127, 위도 37~38)

#### 2. 정변환 테스트
서울 중심 좌표(경도 127.0, 위도 37.5)를 EPSG:5179로 변환:
- **결과**: x=955,805, y=1,944,644
- **현재 데이터**: x=959,822, y=1,950,099
- **차이**: x=4,017m, y=5,455m (약 4~5km 차이)
- **분석**: 위치 차이로 인한 정상적인 범위 내 차이

## EPSG:5179 좌표계 정보

- **명칭**: Korea 2000 / Central Belt 2010
- **단위**: 미터
- **범위**: 
  - x: 약 200,000 ~ 1,000,000
  - y: 약 400,000 ~ 2,000,000
- **용도**: 한국 중부 지역 좌표계

## 좌표 변환 예제

### Python (pyproj 사용)

```python
from pyproj import Transformer

# EPSG:5179 → WGS84 변환
transformer = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
lon, lat = transformer.transform(959822, 1950099)
print(f"경도: {lon:.6f}, 위도: {lat:.6f}")

# WGS84 → EPSG:5179 변환
transformer_reverse = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
x, y = transformer_reverse.transform(127.0, 37.5)
print(f"x: {x:.0f}, y: {y:.0f}")
```

### JavaScript (proj4js 사용)

```javascript
const proj4 = require('proj4');

// EPSG:5179 정의
proj4.defs("EPSG:5179", "+proj=tmerc +lat_0=38 +lon_0=127.5 +k=0.9996 +x_0=1000000 +y_0=2000000 +ellps=GRS80 +units=m +no_defs");

// EPSG:5179 → WGS84 변환
const [lon, lat] = proj4("EPSG:5179", "EPSG:4326", [959822, 1950099]);
console.log(`경도: ${lon.toFixed(6)}, 위도: ${lat.toFixed(6)}`);

// WGS84 → EPSG:5179 변환
const [x, y] = proj4("EPSG:4326", "EPSG:5179", [127.0, 37.5]);
console.log(`x: ${x.toFixed(0)}, y: ${y.toFixed(0)}`);
```

## 참고

- SGIS API 문서에서 공식적으로 명시된 좌표계 정보는 확인되지 않았습니다.
- 실제 좌표 변환 테스트를 통해 EPSG:5179로 확인되었습니다.
- 다른 지역 데이터의 경우 좌표 범위가 다를 수 있습니다.

## 관련 파일

- `scripts/analyze_coordinates.py`: 좌표 분석 스크립트
- `scripts/check_sgis_coordinate_system.py`: 좌표계 확인 스크립트
- `scripts/test_coordinate_systems.py`: 다양한 좌표계 테스트 스크립트

