"""
TOPIS 실시간 도로 소통 정보 API 클라이언트

- 서울열린데이터광장 TrafficInfo API (XML)
- 성수 권역 LINK_ID 목록 기반 비동기 병렬 호출
- 메모리 캐시 + TTL 5분
- DB 적재 (traffic_realtime_log) + JSONL 일별 백업
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "pipeline"
REF_FILE = PIPELINE_DIR / "ref" / "topis_seongsu_links.json"
BRONZE_DIR = PIPELINE_DIR / "bronze" / "topis_realtime"

API_BASE = "http://openapi.seoul.go.kr:8088"
CONCURRENCY = 30
CACHE_TTL_SEC = 300  # 5분
RETENTION_DAYS = 90

KST = timezone(timedelta(hours=9))


class TopisTrafficClient:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._ref_data: dict | None = None
        self._cache: dict | None = None
        self._cache_ts: float = 0
        self._last_cleanup_date: str = ""

    def _load_ref(self) -> dict:
        if self._ref_data is None:
            with open(REF_FILE, encoding="utf-8") as f:
                self._ref_data = json.load(f)
            logger.info(
                "TOPIS ref loaded: %d links", self._ref_data["meta"]["link_count"]
            )
        return self._ref_data

    async def _fetch_link(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        link_id: str,
    ) -> tuple[str, dict | None]:
        async with semaphore:
            url = f"{API_BASE}/{self._api_key}/xml/TrafficInfo/1/1/{link_id}"
            try:
                resp = await client.get(url, timeout=10.0)
                spd = re.search(r"<prcs_spd>(.*?)</prcs_spd>", resp.text)
                trv = re.search(r"<prcs_trv_time>(.*?)</prcs_trv_time>", resp.text)
                if spd:
                    return link_id, {
                        "speed": float(spd.group(1)),
                        "travel_time": float(trv.group(1)) if trv else 0,
                    }
            except Exception as e:
                logger.warning("TOPIS fetch failed for %s: %s", link_id, e)
            return link_id, None

    async def _fetch_all(self) -> dict[str, dict]:
        ref = self._load_ref()
        link_ids = ref["link_ids"]
        semaphore = asyncio.Semaphore(CONCURRENCY)
        results: dict[str, dict] = {}

        async with httpx.AsyncClient() as client:
            tasks = [
                self._fetch_link(client, semaphore, lid) for lid in link_ids
            ]
            for coro in asyncio.as_completed(tasks):
                lid, data = await coro
                if data:
                    results[lid] = data

        logger.info("TOPIS fetched %d/%d links", len(results), len(link_ids))
        return results

    def _save_jsonl(self, speed_data: dict[str, dict], fetched_at: datetime):
        """JSONL 일별 파일에 append"""
        try:
            BRONZE_DIR.mkdir(parents=True, exist_ok=True)
            fname = fetched_at.strftime("%Y%m%d") + ".jsonl"
            ts_iso = fetched_at.isoformat()
            with open(BRONZE_DIR / fname, "a", encoding="utf-8") as f:
                for lid, data in speed_data.items():
                    row = {"ts": ts_iso, "link_id": lid, **data}
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            logger.info("JSONL appended: %s (%d rows)", fname, len(speed_data))
        except Exception as e:
            logger.warning("JSONL write failed: %s", e)

    async def _save_db(self, speed_data: dict[str, dict], fetched_at: datetime):
        """DB traffic_realtime_log에 bulk insert"""
        try:
            from app.db.database import is_db_available, async_session
            if not is_db_available() or async_session is None:
                return

            from app.db.models import TrafficRealtimeLog

            rows = [
                TrafficRealtimeLog(
                    fetched_at=fetched_at,
                    link_id=lid,
                    speed=data["speed"],
                    travel_time=data["travel_time"],
                )
                for lid, data in speed_data.items()
            ]

            async with async_session() as session:
                session.add_all(rows)
                await session.commit()

            logger.info("DB inserted %d rows", len(rows))
        except Exception as e:
            logger.warning("DB insert failed: %s", e)

    async def _cleanup_old(self, now: datetime):
        """90일 이전 데이터 삭제 (하루 1회)"""
        today_str = now.strftime("%Y%m%d")
        if self._last_cleanup_date == today_str:
            return
        self._last_cleanup_date = today_str

        try:
            from app.db.database import is_db_available, async_session
            if not is_db_available() or async_session is None:
                return

            from sqlalchemy import delete
            from app.db.models import TrafficRealtimeLog

            cutoff = now - timedelta(days=RETENTION_DAYS)
            async with async_session() as session:
                result = await session.execute(
                    delete(TrafficRealtimeLog).where(TrafficRealtimeLog.fetched_at < cutoff)
                )
                await session.commit()
                deleted = result.rowcount
                if deleted > 0:
                    logger.info("DB cleanup: deleted %d rows older than %s", deleted, cutoff.isoformat())
        except Exception as e:
            logger.warning("DB cleanup failed: %s", e)

    async def get_realtime(self) -> dict:
        """캐시된 실시간 교통 데이터 반환 (TTL 초과 시 갱신 + 적재)"""
        now = time.time()
        if self._cache and (now - self._cache_ts) < CACHE_TTL_SEC:
            return self._cache

        ref = self._load_ref()
        speed_data = await self._fetch_all()
        fetched_at = datetime.now(KST)

        # DB 적재 + JSONL 백업 (비동기, 실패해도 응답에 영향 없음)
        await asyncio.gather(
            self._save_db(speed_data, fetched_at),
            asyncio.to_thread(self._save_jsonl, speed_data, fetched_at),
            self._cleanup_old(fetched_at),
            return_exceptions=True,
        )

        segments = []
        for link in ref["links"]:
            lid = link["link_id"]
            rt = speed_data.get(lid)
            if rt is None:
                continue
            segments.append({
                "link_id": lid,
                "road_name": link.get("road_name", ""),
                "direction": link.get("direction", ""),
                "lanes": link.get("lanes", 1),
                "road_type": link.get("road_type", ""),
                "coordinates": link["coordinates"],
                "speed": rt["speed"],
                "travel_time": rt["travel_time"],
            })

        result = {
            "meta": {
                "bbox": ref["meta"]["bbox"],
                "segment_count": len(segments),
                "fetched_at": int(now),
                "cache_ttl": CACHE_TTL_SEC,
            },
            "segments": segments,
        }

        self._cache = result
        self._cache_ts = now
        return result


_client: TopisTrafficClient | None = None


def get_topis_client(api_key: str) -> TopisTrafficClient:
    global _client
    if _client is None:
        if not api_key:
            raise RuntimeError("SEOUL_OPEN_DATA_KEY not set")
        _client = TopisTrafficClient(api_key)
    return _client
