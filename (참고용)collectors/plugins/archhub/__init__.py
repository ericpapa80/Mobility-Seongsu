"""건축Hub(건축서비스산업 정보체계) 수집 플러그인.

- 건축물대장: BldRgstHubService
- 건축인허가: ArchPmsHubService
- .env: 건축Hub_API_KEY (공공데이터포털 서비스 키)
"""

from plugins.archhub.scraper import ArchHubScraper

__all__ = ["ArchHubScraper"]
