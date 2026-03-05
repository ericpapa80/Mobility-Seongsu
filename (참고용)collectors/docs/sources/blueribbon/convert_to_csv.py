"""
기존 JSON 파일을 CSV로 변환하는 유틸리티 스크립트
"""
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
from scraper import BlueRibbonScraper

def main():
    json_file = "restaurants_all.json"
    csv_file = "restaurants_all.csv"
    
    print(f"Loading JSON from {json_file}...", flush=True)
    
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"Loaded {len(data)} restaurants", flush=True)
        
        scraper = BlueRibbonScraper()
        scraper.save_to_csv(data, csv_file)
        
        print(f"\nConversion completed!", flush=True)
        print(f"CSV file: {csv_file}", flush=True)
        
    except FileNotFoundError:
        print(f"Error: {json_file} not found", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

