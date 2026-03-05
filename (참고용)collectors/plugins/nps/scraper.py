"""NPS scraper for collecting National Pension Service data."""

import sys
import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_scraper import BaseScraper
from plugins.nps.normalizer import NPSNormalizer
from plugins.nps.geocoder import Geocoder
from core.logger import get_logger
from core.file_handler import FileHandler
from core.storage.file_storage import FileStorage
from config.scrapers.nps import NPSConfig

logger = get_logger(__name__)


class NPSScraper(BaseScraper):
    """NPS scraper for collecting National Pension Service workplace data.
    
    This scraper collects workplace pension data from NPS CSV files.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize NPS scraper.
        
        Args:
            output_dir: Base output directory for saving data
        """
        super().__init__(name="nps", output_dir=output_dir)
        self.file_handler = FileHandler()
        self.normalizer = NPSNormalizer()
        self.storage = FileStorage(
            base_dir=self.output_dir / "processed",
            config={'source_name': 'nps', 'save_json': True, 'save_csv': True}
        )
        self.geocoder = None  # Lazy initialization
        
        # Preprocessing patterns
        self.pattern1 = re.compile(r'(\([^)]+\))')
        self.pattern2 = re.compile(r'(\[[^)]+\])')
        self.pattern3 = re.compile(r'[^A-Za-z0-9가-힣]')
        
        # Validate configuration
        if not NPSConfig.validate():
            logger.warning("NPS configuration is incomplete. Some features may not work.")
    
    def scrape(
        self,
        csv_file_path: Optional[str] = None,
        filter_address: Optional[str] = None,
        filter_active_only: bool = True,
        add_coordinates: bool = False,
        geocoding_service: str = "kakao",
        geocoding_delay: float = 0.1,
        save_json: bool = True,
        save_csv: bool = True
    ) -> Dict[str, Any]:
        """Scrape NPS workplace data from CSV file.
        
        국민연금 가입 사업장 데이터를 CSV 파일에서 수집합니다.
        
        Args:
            csv_file_path: Path to NPS CSV file (if None, uses default from config)
            filter_address: Address filter (e.g., "성수동" for Seongsu-dong)
            filter_active_only: Whether to filter only active workplaces (가입상태=1)
            add_coordinates: Whether to add geocoded coordinates (x, y) to records
            geocoding_service: Geocoding service to use ("kakao" or "vworld")
            geocoding_delay: Delay between geocoding requests (seconds) to avoid rate limiting
            save_json: Whether to save as JSON
            save_csv: Whether to save as CSV
            
        Returns:
            Dictionary containing scraped data with 'data', 'files', and 'timestamp' keys
            
        Example:
            >>> scraper = NPSScraper()
            >>> result = scraper.scrape(
            ...     csv_file_path="data/nps.csv",
            ...     filter_address="성수동",
            ...     filter_active_only=True
            ... )
        """
        logger.info("Starting NPS workplace data scraping")
        
        # Get CSV file path
        if csv_file_path is None:
            csv_file_path = NPSConfig.get_default_csv_path()
        
        csv_path = Path(csv_file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"NPS CSV file not found: {csv_path}")
        
        logger.info(f"Loading CSV file: {csv_path}")
        
        try:
            # Load CSV file
            df = pd.read_csv(csv_path, encoding='cp949', low_memory=False)
            
            # Preprocess data
            df = self._preprocess_data(df)
            
            # Apply filters
            if filter_active_only:
                df = df[df['가입상태'] == 1]
                logger.info(f"Filtered to active workplaces: {len(df)} records")
            
            if filter_address:
                # 주소 필터링 (NaN 처리 및 타입 변환)
                # 우선순위: 1) 사업장지번상세주소에서 정확한 동 검색, 2) 주소 필드에서 검색
                
                filter_text = str(filter_address).strip()
                initial_count = len(df)
                
                # Strategy 1: 사업장지번상세주소에서 '성수동1가' 또는 '성수동2가' 우선 검색
                if '사업장지번상세주소' in df.columns:
                    def jibun_filter(jibun_addr):
                        if pd.isna(jibun_addr):
                            return False
                        jibun_str = str(jibun_addr)
                        # 성수동1가 또는 성수동2가 포함 확인
                        return '성수동1가' in jibun_str or '성수동2가' in jibun_str
                    
                    jibun_mask = df['사업장지번상세주소'].apply(jibun_filter)
                    jibun_count = jibun_mask.sum()
                    
                    if jibun_count > 0:
                        df = df[jibun_mask]
                        logger.info(f"Filtered by '사업장지번상세주소' (성수동1가/2가): {len(df)} records")
                    else:
                        # Strategy 2: 주소 필드에서 검색 (fallback)
                        if '주소' not in df.columns:
                            logger.warning("'주소' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: " + str(df.columns.tolist()[:10]))
                        else:
                            def contains_filter(addr):
                                if pd.isna(addr):
                                    return False
                                return filter_text in str(addr)
                            
                            mask = df['주소'].apply(contains_filter)
                            df = df[mask]
                            logger.info(f"Filtered by address '{filter_text}': {len(df)} records")
                else:
                    # Strategy 2: 주소 필드에서 검색 (사업장지번상세주소가 없는 경우)
                    if '주소' not in df.columns:
                        logger.warning("'주소' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: " + str(df.columns.tolist()[:10]))
                    else:
                        def contains_filter(addr):
                            if pd.isna(addr):
                                return False
                            return filter_text in str(addr)
                        
                        mask = df['주소'].apply(contains_filter)
                        df = df[mask]
                        logger.info(f"Filtered by address '{filter_text}': {len(df)} records")
            
            # Add coordinates if requested
            if add_coordinates:
                logger.info("Adding coordinates via geocoding (Kakao/Naver priority, parallel processing)...")
                df = self._add_coordinates(df, geocoding_service, geocoding_delay, workers=10)
            
            # Convert to dictionary format
            data = {
                'total_count': len(df),
                'records': df.to_dict('records')
            }
            
            # Validate data
            if not self.validate(data):
                logger.warning("Data validation failed, but continuing...")
            
            # Save raw data
            saved_files = {}
            timestamp = self._get_timestamp()
            
            folder_name = f"nps_{timestamp}"
            output_dir = self.raw_dir / folder_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if save_json:
                json_path = output_dir / f"nps_{timestamp}.json"
                saved_files['json'] = self.file_handler.save_json(data, json_path)
                logger.info(f"Raw data saved as JSON: {saved_files['json']}")
            
            if save_csv:
                csv_path = output_dir / f"nps_{timestamp}.csv"
                saved_files['csv'] = self.file_handler.save_csv(df.to_dict('records'), csv_path)
                logger.info(f"Raw data saved as CSV: {saved_files['csv']}")
            
            # Normalize and save processed data
            metadata = {
                'csv_source': str(csv_path),
                'filter_address': filter_address,
                'filter_active_only': filter_active_only,
                'total_count': len(df),
                'timestamp': timestamp,
                'folder_name': folder_name
            }
            normalized_data = self.normalizer.normalize(data, metadata)
            processed_path = self.storage.save(normalized_data, metadata)
            saved_files['processed'] = processed_path
            logger.info(f"Normalized data saved to: {processed_path}")
            
            logger.info("NPS workplace data scraping completed successfully")
            return {
                'data': data,
                'files': saved_files,
                'timestamp': timestamp,
                'total_count': len(df),
                'filter_address': filter_address,
                'filter_active_only': filter_active_only
            }
            
        except Exception as e:
            logger.error(f"Error during NPS scraping: {e}")
            raise
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess NPS data.
        
        Args:
            df: Raw DataFrame from CSV
            
        Returns:
            Preprocessed DataFrame
        """
        # Rename columns
        df.columns = [
            '자료생성년월', '사업장명', '사업자등록번호', '가입상태', '우편번호',
            '사업장지번상세주소', '주소', '고객법정동주소코드', '고객행정동주소코드', 
            '시도코드', '시군구코드', '읍면동코드', 
            '사업장형태구분코드', '업종코드', '업종코드명', 
            '적용일자', '재등록일자', '탈퇴일자',
            '가입자수', '금액', '신규', '상실'
        ]
        
        # Clean business name
        df['사업장명'] = df['사업장명'].apply(self._preprocess_business_name)
        
        # Extract address components
        df['시도'] = df['주소'].str.split(' ').str[0]
        
        # Calculate derived fields
        df['인당금액'] = df['금액'] / df['가입자수'].replace(0, 1)  # Avoid division by zero
        df['월급여추정'] = df['인당금액'] / 9 * 100
        df['연간급여추정'] = df['월급여추정'] * 12
        
        # Process dates
        if '탈퇴일자' in df.columns:
            df['탈퇴일자_연도'] = pd.to_datetime(df['탈퇴일자'], errors='coerce').dt.year
            df['탈퇴일자_월'] = pd.to_datetime(df['탈퇴일자'], errors='coerce').dt.month
        
        return df
    
    def _preprocess_business_name(self, name: str) -> str:
        """Preprocess business name by removing parentheses and brackets.
        
        Args:
            name: Business name
            
        Returns:
            Cleaned business name
        """
        if pd.isna(name):
            return ""
        
        name = str(name)
        name = self.pattern1.sub('', name)
        name = self.pattern2.sub('', name)
        name = self.pattern3.sub(' ', name)
        name = re.sub(r' +', ' ', name)
        return name.strip()
    
    def _add_coordinates(self, df: pd.DataFrame, service: str = "kakao", delay: float = 0.1, workers: int = 10) -> pd.DataFrame:
        """Add coordinates to DataFrame using geocoding with parallel processing.
        
        Args:
            df: DataFrame with address column
            service: Geocoding service to use (ignored, uses kakao/naver priority)
            delay: Delay between requests
            workers: Number of parallel workers
            
        Returns:
            DataFrame with added x, y columns (lon/lat removed, using x/y only)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        import time
        
        # Initialize coordinate columns (x, y only)
        df['x'] = None
        df['y'] = None
        
        total = len(df)
        success_count = 0
        fail_count = 0
        
        # Thread-safe counter
        counter_lock = threading.Lock()
        
        def geocode_record(args):
            """Geocode a single record"""
            idx, row, delay_val = args
            
            address = row.get('주소', '')
            business_name = row.get('사업장명', '')
            jibun_address = row.get('사업장지번상세주소', '')
            
            # 주소 선택
            if pd.isna(address) or not str(address).strip() or str(address).strip() == 'nan':
                if pd.isna(jibun_address) or not str(jibun_address).strip() or str(jibun_address).strip() == 'nan':
                    return (idx, None)
                address = jibun_address
            
            address_str = str(address).strip()
            if not address_str or address_str == 'nan':
                return (idx, None)
            
            business_name_str = str(business_name).strip() if not pd.isna(business_name) and str(business_name).strip() != 'nan' else None
            
            coords = None
            
            # Strategy 1: Kakao API (상호명 + 주소)
            if business_name_str:
                try:
                    kakao_geocoder = Geocoder(service="kakao")
                    coords = kakao_geocoder.geocode(address_str, keyword=business_name_str, delay=delay_val)
                    kakao_geocoder.close()
                    if coords:
                        return (idx, coords)
                except Exception as e:
                    logger.debug(f"Kakao geocoding failed: {e}")
            
            # Strategy 2: Naver API (상호명 + 주소)
            if business_name_str:
                try:
                    naver_geocoder = Geocoder(service="naver")
                    coords = naver_geocoder.geocode(address_str, keyword=business_name_str, delay=delay_val)
                    naver_geocoder.close()
                    if coords:
                        return (idx, coords)
                except Exception as e:
                    logger.debug(f"Naver geocoding failed: {e}")
            
            # Strategy 3: Kakao API (주소만)
            try:
                kakao_geocoder = Geocoder(service="kakao")
                coords = kakao_geocoder.geocode(address_str, delay=delay_val)
                kakao_geocoder.close()
                if coords:
                    return (idx, coords)
            except Exception as e:
                logger.debug(f"Kakao address-only geocoding failed: {e}")
            
            # Strategy 4: Naver API (주소만)
            try:
                naver_geocoder = Geocoder(service="naver")
                coords = naver_geocoder.geocode(address_str, delay=delay_val)
                naver_geocoder.close()
                if coords:
                    return (idx, coords)
            except Exception as e:
                logger.debug(f"Naver address-only geocoding failed: {e}")
            
            return (idx, None)
        
        logger.info(f"Geocoding {total} addresses with {workers} parallel workers...")
        start_time = time.time()
        
        # Prepare tasks
        tasks = [(idx, row, delay) for idx, row in df.iterrows()]
        
        # Parallel processing
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {executor.submit(geocode_record, task): task[0] for task in tasks}
            
            for future in as_completed(future_to_idx):
                try:
                    idx, coords = future.result()
                    
                    if coords:
                        df.at[idx, 'x'] = coords.get('x') or coords.get('lon')
                        df.at[idx, 'y'] = coords.get('y') or coords.get('lat')
                        with counter_lock:
                            success_count += 1
                    else:
                        with counter_lock:
                            fail_count += 1
                    
                    # Progress logging
                    completed = success_count + fail_count
                    if completed % 100 == 0 or completed == total:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        logger.info(f"Geocoding progress: {completed}/{total} (성공: {success_count}, 실패: {fail_count}, 속도: {rate:.1f}개/초)")
                
                except Exception as e:
                    idx = future_to_idx[future]
                    logger.error(f"Error processing record {idx}: {e}")
                    with counter_lock:
                        fail_count += 1
        
        elapsed_time = time.time() - start_time
        logger.info(f"Geocoding completed: {success_count}/{total} addresses geocoded successfully in {elapsed_time:.1f} seconds")
        
        return df
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string.
        
        Returns:
            Timestamp string in format: YYYYMMDD_HHMMSS
        """
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def find_company(self, company_name: str, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Find companies by name.
        
        Args:
            company_name: Company name to search
            df: Optional DataFrame to search in (if None, needs to scrape first)
            
        Returns:
            DataFrame with matching companies
        """
        if df is None:
            raise ValueError("DataFrame must be provided or scrape() must be called first")
        
        return df[df['사업장명'].str.contains(company_name, na=False)].sort_values(
            '가입자수', ascending=False
        )
    
    def close(self):
        """Close storage and cleanup."""
        if self.geocoder:
            self.geocoder.close()
        self.storage.close()
        logger.info("NPS scraper closed")

