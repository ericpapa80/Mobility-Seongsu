# 정제된 데이터 삭제 가이드

## `data/processed/sgis/` 폴더의 역할

`data/processed/sgis/` 폴더에는 **정제된(normalized) 데이터**가 저장됩니다.

### 정제된 데이터의 특징

1. **공통 스키마로 변환**
   - 원본 데이터를 공통 스키마 형식으로 변환
   - 필드명 표준화 (예: `corp_nm` → `name`, `naddr` → `address`)
   - 중첩 구조 정리 (예: `coordinates` 객체로 그룹화)

2. **메타데이터 추가**
   - `metadata`: 수집 시점, 소스 정보 등
   - `source_specific`: SGIS 특화 정보 (theme_cd, year, adm_cd 등)

3. **원본 데이터 보존**
   - 정제된 각 항목에 `raw` 필드로 원본 데이터 포함

### 정제된 데이터 구조 예시

```json
{
  "metadata": {
    "source": "sgis",
    "collected_at": "2025-12-01T16:57:55",
    "normalized_at": "2025-12-01T16:57:55"
  },
  "source_specific": {
    "theme_cd": 0,
    "year": 2023,
    "adm_cd": "11040"
  },
  "data": {
    "items": [
      {
        "id": "200709598227961950100280",
        "name": "성광금속",
        "address": "서울특별시 성동구 왕십리로14길 9",
        "coordinates": {
          "x": "959822",
          "y": "1950099",
          "x_5179": "",
          "y_5179": "",
          "lon": "",
          "lat": ""
        },
        "administrative_code": "11040660",
        "theme_code": "110",
        "weight": 1,
        "raw": { /* 원본 데이터 */ }
      }
    ],
    "count": 10123
  }
}
```

## 삭제 가능 여부

### ✅ 삭제 가능한 경우

1. **원본 데이터가 있는 경우**
   - `data/raw/sgis/`에 원본 데이터가 있으면 정제된 데이터는 재생성 가능
   - 정제는 단순 변환이므로 원본에서 언제든 재생성 가능

2. **디스크 공간이 부족한 경우**
   - 정제된 데이터는 원본보다 크기가 더 클 수 있음 (메타데이터 추가, 중첩 구조)
   - 필요 시 재생성 가능하므로 삭제해도 무방

3. **원본 데이터만 필요한 경우**
   - 원본 데이터에 이미 필요한 모든 정보가 포함되어 있음
   - WGS84 변환도 원본 폴더에 별도 파일로 저장됨

### ⚠️ 삭제 전 고려사항

1. **재생성 시간**
   - 정제 과정은 빠르지만, 대량 데이터의 경우 시간이 소요될 수 있음
   - 8개 연도 데이터를 재정제하는 데 수 분 소요 가능

2. **다른 시스템 연동**
   - 정제된 데이터는 공통 스키마로 변환되어 다른 시스템과 연동하기 편리
   - 여러 소스의 데이터를 통합 분석할 때 유용

3. **분석 편의성**
   - 정제된 데이터는 구조화되어 있어 분석 도구에서 사용하기 편리
   - 메타데이터가 포함되어 있어 데이터 출처 추적 용이

## 삭제 방법

### 전체 삭제

```bash
# PowerShell
Remove-Item -Path "data\processed\sgis" -Recurse -Force

# 또는 Python
python -c "from pathlib import Path; import shutil; shutil.rmtree('data/processed/sgis')"
```

### 특정 연도만 삭제

```bash
# 특정 타임스탬프 폴더 삭제
Remove-Item -Path "data\processed\sgis\20251201_165755" -Recurse -Force
```

## 재생성 방법

정제된 데이터를 삭제한 후 재생성이 필요한 경우:

1. **자동 재생성**: 다음 수집 시 자동으로 생성됨
2. **수동 재생성**: 원본 데이터를 읽어서 정제 스크립트 실행

```python
from plugins.sgis.normalizer import SGISNormalizer
from core.storage.file_storage import FileStorage
import json

# 원본 데이터 읽기
with open('data/raw/sgis/.../sgis_technical_biz_2023_...json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# 정제
normalizer = SGISNormalizer()
normalized = normalizer.normalize(raw_data, metadata={'year': 2023, ...})

# 저장
storage = FileStorage(base_dir=Path('data/processed'), config={'source_name': 'sgis'})
storage.save(normalized, metadata)
```

## 권장 사항

### 현재 상황에서의 권장사항

1. **원본 데이터가 충분한 경우**: ✅ **삭제 가능**
   - 원본 데이터(`data/raw/sgis/`)에 모든 정보 포함
   - WGS84 변환 파일도 원본 폴더에 저장됨
   - 필요 시 재생성 가능

2. **디스크 공간 절약**: ✅ **삭제 권장**
   - 정제된 데이터는 원본보다 크기가 더 클 수 있음
   - 원본 데이터만으로도 충분히 활용 가능

3. **향후 확장 고려**: ⚠️ **보관 고려**
   - 여러 소스 데이터를 통합 분석할 계획이 있다면 보관
   - 공통 스키마로 변환된 데이터가 유용할 수 있음

## 결론

**`data/processed/sgis/` 폴더의 파일들은 삭제해도 됩니다.**

- 원본 데이터가 있으면 언제든 재생성 가능
- 현재는 원본 데이터만으로도 충분히 활용 가능
- 디스크 공간 절약 가능

단, 향후 여러 소스 데이터를 통합 분석할 계획이 있다면 정제된 데이터를 보관하는 것도 고려할 수 있습니다.




