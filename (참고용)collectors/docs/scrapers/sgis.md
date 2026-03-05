# SGIS 스크래이퍼 가이드

## 개요

SGIS(통계지리정보서비스) 기술업종 통계지도에서 POI 회사 밀도 데이터를 수집하는 스크래이퍼입니다.

## 기능

- 기술업종 통계지도 데이터 수집
- 지도 범위(bounds) 지정 가능
- 줌 레벨 지정 가능
- JSON 및 CSV 형식으로 데이터 저장

## 설정

### 환경 변수

`.env` 파일에 다음 변수를 설정하세요:

```env
SGIS_CONSUMER_KEY=your_consumer_key_here
SGIS_CONSUMER_SECRET=your_consumer_secret_here
```

### 설정 검증

```python
from config.scrapers.sgis import SGISConfig

if not SGISConfig.validate():
    print("SGIS 설정이 올바르지 않습니다.")
```

## 사용 방법

### 통합 실행기 사용

```bash
# 기본 실행
python -m core.runner run sgis

# JSON만 저장
python -m core.runner run sgis --json-only

# 출력 디렉토리 지정
python -m core.runner run sgis --output-dir /path/to/output
```

### 개별 스크립트 사용

```bash
# 기본 실행
python scripts/scrapers/run_sgis.py

# 지도 범위 지정
python scripts/scrapers/run_sgis.py --bounds "37.6,37.4,127.1,126.9"

# 줌 레벨 지정
python scripts/scrapers/run_sgis.py --zoom 10

# 범위와 줌 레벨 함께 지정
python scripts/scrapers/run_sgis.py --bounds "37.6,37.4,127.1,126.9" --zoom 10

# JSON만 저장
python scripts/scrapers/run_sgis.py --json-only

# 콘솔에만 출력
python scripts/scrapers/run_sgis.py --no-save
```

### 프로그래밍 방식

```python
from plugins.sgis.scraper import SGISScraper
from pathlib import Path

# 스크래이퍼 생성
scraper = SGISScraper()

# 기본 수집
result = scraper.scrape()

# 지도 범위 지정하여 수집
bounds = {
    'north': 37.6,
    'south': 37.4,
    'east': 127.1,
    'west': 126.9
}
result = scraper.scrape(bounds=bounds, zoom_level=10)

# 결과 확인
print(f"수집된 데이터: {result['data']}")
print(f"저장된 파일: {result['files']}")

# 정리
scraper.close()
```

## API 엔드포인트

- **URL**: `https://sgis.mods.go.kr/ServiceAPI/technicalBiz/getPoiCompanyDensity.json`
- **Method**: POST
- **Content-Type**: `application/x-www-form-urlencoded`

## 파라미터

### bounds (선택사항)

지도 범위를 지정합니다.

```python
bounds = {
    'north': 37.6,  # 북쪽 위도
    'south': 37.4,  # 남쪽 위도
    'east': 127.1,  # 동쪽 경도
    'west': 126.9   # 서쪽 경도
}
```

### zoom_level (선택사항)

지도의 줌 레벨을 지정합니다. 숫자가 클수록 더 상세한 데이터를 수집합니다.

## 데이터 저장 위치

수집된 데이터는 다음 위치에 저장됩니다:

- **원본 데이터**: `data/raw/sgis/{timestamp}/`
  - JSON: `sgis_technical_biz_{timestamp}.json`
  - CSV: `sgis_technical_biz_{timestamp}.csv`

## 예제

### 서울 지역 데이터 수집

```bash
python scripts/scrapers/run_sgis.py \
  --bounds "37.7,37.4,127.2,126.8" \
  --zoom 12
```

### 부산 지역 데이터 수집

```bash
python scripts/scrapers/run_sgis.py \
  --bounds "35.3,35.0,129.2,128.9" \
  --zoom 11
```

## 문제 해결

### 인증 오류

- `.env` 파일의 `SGIS_CONSUMER_KEY`와 `SGIS_CONSUMER_SECRET`이 올바른지 확인
- 키가 만료되지 않았는지 확인

### 데이터가 비어있는 경우

- 지도 범위(bounds)가 올바른지 확인
- API 응답을 확인하기 위해 `--no-save` 옵션으로 실행

### API 오류

- 네트워크 연결 확인
- API 서버 상태 확인
- 로그 파일 확인: `logs/sgis/sgis_YYYYMMDD.log`

## 참고

- [SGIS 출처 정보](../sources/sgis/sgis.md): API 상세 정보
- [환경 변수 가이드](../project/ENV_GUIDE.md): 환경 변수 설정 방법

