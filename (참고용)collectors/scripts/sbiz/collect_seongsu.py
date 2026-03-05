"""성수동 상가업소 데이터 수집 스크립트."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.scraper import SBIZScraper
from core.logger import get_logger

logger = get_logger(__name__)


def main():
    """성동구(11200) 시군구 단위 상가업소 데이터 수집."""
    # 11200: 서울시 성동구 시군구 코드
    # 참조: https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong?divId=signguCd&key=11200
    target = {
        "cd": "11200",
        "nm": "성동구",
        "div_id": "signguCd"  # 시군구 코드
    }
    
    scraper = SBIZScraper()
    
    try:
        logger.info(f"=" * 60)
        logger.info(f"수집 시작: {target['nm']} (시군구코드: {target['cd']})")
        logger.info(f"=" * 60)
        try:
            result = scraper.scrape(
                adong_cd=target['cd'],
                adong_nm=target['nm'],
                save_json=True,
                save_csv=True,
                div_id=target['div_id']
            )
            logger.info(f"✓ {target['nm']} 수집 완료: {result['count']}개 업소")
            logger.info(f"  JSON: {result['files'].get('json', 'N/A')}")
            logger.info(f"  CSV: {result['files'].get('csv', 'N/A')}")
        except Exception as e:
            logger.error(f"✗ {target['nm']} 수집 실패: {e}")
            import traceback
            traceback.print_exc()
    finally:
        scraper.close()


if __name__ == "__main__":
    main()

