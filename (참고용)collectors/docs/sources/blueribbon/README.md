# BlueRibbon 스크레이핑 프로젝트

BlueRibbon 사이트의 레스토랑 정보를 스크레이핑하는 Python 스크립트입니다.

## 설치

```bash
pip install -r requirements.txt
```

## 사용 방법

### 기본 사용

```python
from scraper import BlueRibbonScraper

scraper = BlueRibbonScraper()

# Cookie와 CSRF 토큰 업데이트 (필수)
scraper.update_cookies("JSESSIONID=...; _gid=...; ...")
scraper.update_csrf_token("토큰값")

# 첫 페이지 가져오기
response = scraper.fetch_restaurants(page=0, size=32)
restaurants = scraper.extract_restaurant_data(response)

# JSON 파일로 저장
scraper.save_to_json(restaurants, "restaurants.json")
```

### 모든 페이지 스크레이핑

```python
# 모든 페이지 스크레이핑 (페이지 간 1초 대기)
all_restaurants = scraper.scrape_all_pages(delay=1.0)

# 최대 5페이지만 스크레이핑
all_restaurants = scraper.scrape_all_pages(max_pages=5, delay=1.0)
```

## 중요 사항

1. **Cookie와 CSRF 토큰 업데이트 필수**
   - `스크레이핑 사이트_정보.md` 파일의 최신 Cookie와 x-csrf-token 값을 사용해야 합니다.
   - 이 값들은 세션마다 달라질 수 있으므로 정기적으로 업데이트가 필요합니다.

2. **요청 간격 조절**
   - 서버 부하를 방지하기 위해 `delay` 파라미터로 요청 간격을 조절하세요.

3. **에러 처리**
   - 네트워크 오류나 API 변경 시 적절한 에러 처리가 필요합니다.

## API 파라미터

- `page`: 페이지 번호 (기본값: 0)
- `size`: 페이지당 항목 수 (기본값: 32)
- `ribbonType`: 리본 타입 (기본값: 모든 타입)
- `year`: 연도 (기본값: 2026)
- `sort`: 정렬 방식 (기본값: updatedDate,desc)

자세한 파라미터는 `scraper.py`의 `fetch_restaurants` 메서드를 참고하세요.

