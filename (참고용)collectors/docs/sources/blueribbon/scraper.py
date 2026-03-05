"""
BlueRibbon 사이트 스크레이핑 스크립트
"""
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import json
import time
import os
import re
from typing import Dict, List, Optional
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


class BlueRibbonScraper:
    def __init__(self):
        self.base_url = "https://www.bluer.co.kr"
        self.api_url = f"{self.base_url}/api/v1/restaurants"
        
        # Request Headers (스크레이핑 사이트_정보.md 참고)
        self.headers = {
            "accept": "application/hal+json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "ko,en;q=0.9,en-US;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.bluer.co.kr/search/ribbon?sort=updatedDate,desc",
            "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "x-requested-with": "XMLHttpRequest",
        }
        
        # 주의: Cookie와 x-csrf-token은 세션마다 달라질 수 있으므로 
        # 실제 사용 시 최신 값으로 업데이트 필요
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 병렬 수집을 위한 락
        self.lock = Lock()
    
    def update_cookies(self, cookies: str):
        """Cookie 문자열을 업데이트합니다."""
        cookie_dict = {}
        for item in cookies.split('; '):
            if '=' in item:
                key, value = item.split('=', 1)
                cookie_dict[key] = value
        self.session.cookies.update(cookie_dict)
    
    def update_csrf_token(self, token: str):
        """CSRF 토큰을 업데이트합니다."""
        self.session.headers['x-csrf-token'] = token
    
    def fetch_restaurants(
        self,
        page: int = 0,
        size: int = 32,
        ribbon_type: str = "RIBBON_THREE,RIBBON_TWO,RIBBON_ONE,NOT,ATTENTION",
        year: int = 2026,
        sort: str = "updatedDate,desc",
        **kwargs
    ) -> Optional[Dict]:
        """
        레스토랑 목록을 가져옵니다.
        
        Args:
            page: 페이지 번호 (기본값: 0)
            size: 페이지당 항목 수 (기본값: 32)
            ribbon_type: 리본 타입 (기본값: 모든 타입)
            year: 연도 (기본값: 2026)
            sort: 정렬 방식 (기본값: updatedDate,desc)
            **kwargs: 추가 쿼리 파라미터
        
        Returns:
            API 응답 JSON 딕셔너리 또는 None
        """
        params = {
            "query": kwargs.get("query", ""),
            "foodType": kwargs.get("foodType", ""),
            "foodTypeDetail": kwargs.get("foodTypeDetail", ""),
            "feature": kwargs.get("feature", ""),
            "location": kwargs.get("location", ""),
            "locationDetail": kwargs.get("locationDetail", ""),
            "area": kwargs.get("area", ""),
            "areaDetail": kwargs.get("areaDetail", ""),
            "ribbonType": ribbon_type,
            "priceRangeMin": kwargs.get("priceRangeMin", ""),
            "priceRangeMax": kwargs.get("priceRangeMax", ""),
            "week": kwargs.get("week", ""),
            "hourMin": kwargs.get("hourMin", ""),
            "hourMax": kwargs.get("hourMax", ""),
            "year": year,
            "recommended": kwargs.get("recommended", False),
            "sort": sort,
            "isSearchName": kwargs.get("isSearchName", False),
            "isBrand": kwargs.get("isBrand", False),
            "isAround": kwargs.get("isAround", False),
            "isMap": kwargs.get("isMap", False),
            "isMapList": kwargs.get("isMapList", False),
            "distance": kwargs.get("distance", 1000),
            "zone1": kwargs.get("zone1", ""),
            "zone2": kwargs.get("zone2", ""),
            "food1": kwargs.get("food1", ""),
            "food2": kwargs.get("food2", ""),
            "zone2Lat": kwargs.get("zone2Lat", ""),
            "zone2Lng": kwargs.get("zone2Lng", ""),
            "page": page,
            "size": size,
        }
        
        try:
            response = self.session.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}", flush=True)
            return None
    
    def extract_restaurant_data(self, response: Dict) -> List[Dict]:
        """
        API 응답에서 레스토랑 데이터를 추출합니다.
        
        Args:
            response: API 응답 JSON 딕셔너리
        
        Returns:
            레스토랑 데이터 리스트
        """
        restaurants = []
        if response and "_embedded" in response:
            restaurants = response["_embedded"].get("restaurants", [])
        return restaurants
    
    def save_to_json(self, data: List[Dict], filename: str = "restaurants.json"):
        """데이터를 JSON 파일로 저장합니다."""
        print(f"Saving data to {filename}...", flush=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}", flush=True)
    
    def clean_text(self, text: str) -> str:
        """
        텍스트에서 비정상적인 라인 종결자를 제거합니다.
        
        Args:
            text: 정리할 텍스트
        
        Returns:
            정리된 텍스트
        """
        if not isinstance(text, str):
            return text
        
        # Line Separator (U+2028) 및 Paragraph Separator (U+2029) 제거
        text = text.replace('\u2028', ' ')  # Line Separator
        text = text.replace('\u2029', ' ')  # Paragraph Separator
        
        # 일반 줄바꿈을 공백으로 변환 (CSV 내부에서는 줄바꿈이 문제가 될 수 있음)
        text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        
        # 연속된 공백을 하나로 정리
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """
        중첩된 딕셔너리를 평탄화합니다.
        
        Args:
            d: 평탄화할 딕셔너리
            parent_key: 부모 키
            sep: 구분자
        
        Returns:
            평탄화된 딕셔너리
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # 리스트는 문자열로 변환 (CSV 호환)
                if len(v) > 0 and isinstance(v[0], dict):
                    # 딕셔너리 리스트는 JSON 문자열로 변환
                    json_str = json.dumps(v, ensure_ascii=False)
                    items.append((new_key, self.clean_text(json_str)))
                else:
                    list_str = ', '.join(str(x) for x in v) if v else ''
                    items.append((new_key, self.clean_text(list_str)))
            else:
                # 문자열 값 정리
                if isinstance(v, str):
                    items.append((new_key, self.clean_text(v)))
                else:
                    items.append((new_key, v))
        return dict(items)
    
    def save_to_csv(self, data: List[Dict], filename: str = "restaurants.csv"):
        """
        데이터를 CSV 파일로 저장합니다.
        
        Args:
            data: 레스토랑 데이터 리스트
            filename: 저장할 파일명
        """
        try:
            import pandas as pd
        except ImportError:
            print("pandas is required for CSV export. Install it with: pip install pandas", flush=True)
            return
        
        print(f"Converting to CSV and saving to {filename}...", flush=True)
        
        # 데이터 평탄화
        flattened_data = []
        for restaurant in data:
            flattened = self.flatten_dict(restaurant)
            flattened_data.append(flattened)
        
        # DataFrame 생성
        df = pd.DataFrame(flattened_data)
        
        # CSV 저장 (UTF-8 BOM 포함하여 Excel에서도 한글 깨짐 방지)
        # lineterminator를 명시적으로 설정하여 표준 라인 종결자 사용
        df.to_csv(
            filename, 
            index=False, 
            encoding='utf-8-sig',
            lineterminator='\n',  # 표준 라인 종결자 사용
            quoting=1  # QUOTE_ALL: 모든 필드를 따옴표로 감싸서 특수문자 문제 방지
        )
        
        print(f"CSV data saved to {filename}", flush=True)
        print(f"Total columns: {len(df.columns)}", flush=True)
        print(f"Total rows: {len(df)}", flush=True)
    
    def scrape_all_pages(self, max_pages: Optional[int] = None, delay: float = 1.0) -> List[Dict]:
        """
        모든 페이지를 스크레이핑합니다.
        
        Args:
            max_pages: 최대 페이지 수 (None이면 모든 페이지)
            delay: 페이지 간 대기 시간 (초)
        
        Returns:
            모든 레스토랑 데이터 리스트
        """
        all_restaurants = []
        page = 0
        
        while True:
            print(f"Scraping page {page}...", flush=True)
            response = self.fetch_restaurants(page=page)
            
            if not response:
                print(f"Failed to fetch page {page}", flush=True)
                break
            
            restaurants = self.extract_restaurant_data(response)
            
            if not restaurants:
                print(f"No more data on page {page}", flush=True)
                break
            
            all_restaurants.extend(restaurants)
            print(f"Page {page}: Collected {len(restaurants)} restaurants (Total: {len(all_restaurants)})", flush=True)
            
            # 다음 페이지가 있는지 확인
            page_info = response.get("page", {})
            total_pages = page_info.get("totalPages", 0)
            current_page = page_info.get("number", page)
            
            if max_pages and page >= max_pages - 1:
                print(f"Reached maximum pages ({max_pages})", flush=True)
                break
            
            if total_pages > 0 and page >= total_pages - 1:
                print(f"All pages collected (Total: {total_pages} pages)", flush=True)
                break
            
            page += 1
            time.sleep(delay)  # 서버 부하 방지
        
        print(f"\nTotal {len(all_restaurants)} restaurants collected", flush=True)
        return all_restaurants
    
    def scrape_all_pages_parallel(
        self, 
        max_pages: Optional[int] = None, 
        max_workers: int = 5,
        delay: float = 0.1
    ) -> List[Dict]:
        """
        모든 페이지를 병렬로 스크레이핑합니다.
        
        Args:
            max_pages: 최대 페이지 수 (None이면 모든 페이지)
            max_workers: 동시 요청 수 (기본값: 5)
            delay: 요청 간 최소 대기 시간 (초, 기본값: 0.1)
        
        Returns:
            모든 레스토랑 데이터 리스트
        """
        # 먼저 첫 페이지를 가져와서 총 페이지 수 확인
        print("Fetching first page to determine total pages...", flush=True)
        first_response = self.fetch_restaurants(page=0)
        
        if not first_response:
            print("Failed to fetch first page", flush=True)
            return []
        
        first_restaurants = self.extract_restaurant_data(first_response)
        if not first_restaurants:
            print("No data found", flush=True)
            return []
        
        page_info = first_response.get("page", {})
        total_pages = page_info.get("totalPages", 0)
        
        if total_pages == 0:
            # 페이지 정보가 없으면 순차 수집으로 전환
            print("Page info not available, switching to sequential scraping...", flush=True)
            return self.scrape_all_pages(max_pages=max_pages, delay=delay)
        
        # 최대 페이지 수 제한
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"Total pages to scrape: {total_pages}", flush=True)
        print(f"Using {max_workers} parallel workers", flush=True)
        
        all_restaurants = []
        all_restaurants.extend(first_restaurants)
        print(f"Page 0: Collected {len(first_restaurants)} restaurants (Total: {len(all_restaurants)})", flush=True)
        
        # 나머지 페이지들을 병렬로 수집
        results = {}
        completed_count = 1  # 첫 페이지는 이미 완료
        
        def fetch_page(page_num: int) -> tuple:
            """단일 페이지를 가져오는 함수"""
            time.sleep(delay)  # 요청 간 최소 대기
            response = self.fetch_restaurants(page=page_num)
            if response:
                restaurants = self.extract_restaurant_data(response)
                return (page_num, restaurants, True)
            return (page_num, [], False)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 페이지 작업 제출
            future_to_page = {
                executor.submit(fetch_page, page): page 
                for page in range(1, total_pages)
            }
            
            # 완료된 작업 처리
            for future in as_completed(future_to_page):
                page_num, restaurants, success = future.result()
                
                if success and restaurants:
                    with self.lock:
                        all_restaurants.extend(restaurants)
                        completed_count += 1
                        print(
                            f"Page {page_num}: Collected {len(restaurants)} restaurants "
                            f"(Total: {len(all_restaurants)}, Progress: {completed_count}/{total_pages})",
                            flush=True
                        )
                else:
                    print(f"Failed to fetch page {page_num}", flush=True)
        
        # 페이지 번호 순서대로 정렬 (선택사항)
        # 실제로는 이미 순서대로 추가되지만, 병렬 처리로 인한 순서 보장을 위해
        # 필요시 정렬할 수 있습니다.
        
        print(f"\nTotal {len(all_restaurants)} restaurants collected", flush=True)
        return all_restaurants
    
    @staticmethod
    def load_config_from_file(filename: str = "스크레이핑 사이트_정보.md") -> Dict[str, str]:
        """
        스크레이핑 사이트_정보.md 파일에서 Cookie와 CSRF 토큰을 읽어옵니다.
        
        Args:
            filename: 설정 파일 경로
        
        Returns:
            {"cookie": "...", "csrf_token": "..."} 딕셔너리
        """
        config = {"cookie": "", "csrf_token": ""}
        
        if not os.path.exists(filename):
            print(f"Warning: {filename} file not found.", flush=True)
            return config
        
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Cookie 추출
            cookie_match = re.search(r'^cookie\s*\n(.+?)(?=\n\w+:|$)', content, re.MULTILINE | re.DOTALL)
            if cookie_match:
                config["cookie"] = cookie_match.group(1).strip()
            
            # CSRF 토큰 추출
            csrf_match = re.search(r'^x-csrf-token\s*\n(.+?)(?=\n\w+:|$)', content, re.MULTILINE | re.DOTALL)
            if csrf_match:
                config["csrf_token"] = csrf_match.group(1).strip()
            
        except Exception as e:
            print(f"Error reading config file: {e}", flush=True)
        
        return config


def main():
    """메인 실행 함수 - 모든 페이지 수집"""
    scraper = BlueRibbonScraper()
    
    # 스크레이핑 사이트_정보.md 파일에서 Cookie와 CSRF 토큰 자동 로드
    print("Loading Cookie and CSRF token from config file...", flush=True)
    config = BlueRibbonScraper.load_config_from_file("스크레이핑 사이트_정보.md")
    
    if config["cookie"]:
        scraper.update_cookies(config["cookie"])
        print("[OK] Cookie configured", flush=True)
    else:
        print("[WARNING] Cookie not found. Please set manually.", flush=True)
    
    if config["csrf_token"]:
        scraper.update_csrf_token(config["csrf_token"])
        print("[OK] CSRF token configured", flush=True)
    else:
        print("[WARNING] CSRF token not found. Please set manually.", flush=True)
    
    # 모든 페이지 수집 시작
    print("\n" + "="*50, flush=True)
    print("Starting to scrape all pages", flush=True)
    print("="*50 + "\n", flush=True)
    
    # 병렬 수집 사용 여부 설정
    USE_PARALLEL = True  # True: 병렬 수집, False: 순차 수집
    MAX_WORKERS = 5      # 동시 요청 수 (병렬 수집 시)
    
    if USE_PARALLEL:
        print(f"Using parallel scraping with {MAX_WORKERS} workers", flush=True)
        all_restaurants = scraper.scrape_all_pages_parallel(max_workers=MAX_WORKERS, delay=0.1)
    else:
        print("Using sequential scraping", flush=True)
        # 페이지 간 1초 대기 (서버 부하 방지)
        all_restaurants = scraper.scrape_all_pages(delay=1.0)
    
    if all_restaurants:
        # 전체 데이터 저장
        output_json = "restaurants_all.json"
        output_csv = "restaurants_all.csv"
        
        scraper.save_to_json(all_restaurants, output_json)
        scraper.save_to_csv(all_restaurants, output_csv)
        
        # 통계 정보 출력
        print("\n" + "="*50, flush=True)
        print("Collection Statistics", flush=True)
        print("="*50, flush=True)
        print(f"Total restaurants: {len(all_restaurants)}", flush=True)
        print(f"JSON file: {output_json}", flush=True)
        print(f"CSV file: {output_csv}", flush=True)
        
        # 리본 타입별 통계
        ribbon_counts = {}
        for restaurant in all_restaurants:
            ribbon_type = restaurant.get("headerInfo", {}).get("ribbonType", "UNKNOWN")
            ribbon_counts[ribbon_type] = ribbon_counts.get(ribbon_type, 0) + 1
        
        if ribbon_counts:
            print("\nRibbon type statistics:", flush=True)
            for ribbon_type, count in sorted(ribbon_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {ribbon_type}: {count}", flush=True)
    else:
        print("\nNo data collected.", flush=True)
        print("Please check if Cookie and CSRF token are correct.", flush=True)


if __name__ == "__main__":
    main()

