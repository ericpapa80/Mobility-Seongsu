"""서울시 성동구 2023년 데이터 수집"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
# 스크립트 위치: scripts/sgis/collection/run_sgis_seongdong.py
# 프로젝트 루트: scripts/sgis/collection/ -> scripts/sgis/ -> scripts/ -> 프로젝트 루트
script_dir = Path(__file__).resolve().parent  # scripts/sgis/collection/
project_root = script_dir.parent.parent.parent  # 프로젝트 루트 (3단계 위)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.sgis.scraper import SGISScraper

def main():
    print("=" * 60)
    print("SGIS 기술업종 통계지도 데이터 수집")
    print("지역: 서울시 성동구")
    print("연도: 2023")
    print("=" * 60)
    
    try:
        # 스크래이퍼 초기화
        print("\n[1/4] 스크래이퍼 초기화 중...")
        scraper = SGISScraper()
        print("✓ 스크래이퍼 초기화 완료")
        
        # 데이터 수집
        print("\n[2/4] 데이터 수집 중...")
        print("   - 테마 코드: 0")
        print("   - 연도: 2023")
        print("   - 행정구역 코드: 11200 (서울시 성동구)")
        print("   - 데이터 타입: 3")
        
        result = scraper.scrape(
            theme_cd=0,
            year=2023,
            adm_cd='11200',  # 서울시 성동구
            data_type=3,
            save_json=True,
            save_csv=True
        )
        
        print("✓ 데이터 수집 완료")
        
        # 결과 출력
        print("\n[3/4] 수집 결과")
        print("=" * 60)
        print(f"타임스탬프: {result.get('timestamp')}")
        print(f"테마 코드: {result.get('theme_cd')}")
        print(f"연도: {result.get('year')}")
        print(f"행정구역 코드: {result.get('adm_cd')}")
        print(f"데이터 타입: {result.get('data_type')}")
        
        if 'files' in result:
            print("\n저장된 파일:")
            if 'json' in result['files']:
                print(f"  - JSON: {result['files']['json']}")
            if 'csv' in result['files']:
                print(f"  - CSV: {result['files']['csv']}")
        
        # 데이터 샘플 확인
        print("\n[4/4] 데이터 확인")
        print("=" * 60)
        data = result.get('data', {})
        if data:
            print(f"데이터 키: {list(data.keys())}")
            if isinstance(data, dict):
                # 결과가 있는 경우
                if 'result' in data:
                    result_list = data['result']
                    print(f"결과 항목 수: {len(result_list)}")
                    if result_list:
                        print(f"\n첫 번째 항목 샘플:")
                        import json
                        print(json.dumps(result_list[0], ensure_ascii=False, indent=2)[:500])
                elif 'data' in data:
                    print(f"데이터 항목 수: {len(data.get('data', []))}")
                else:
                    print(f"응답 데이터:")
                    import json
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
        
        scraper.close()
        print("\n" + "=" * 60)
        print("✓ 모든 작업 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
