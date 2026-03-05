# -*- coding: utf-8 -*-
"""국민연금 가입 사업장 내역 OpenAPI 클라이언트.

공공데이터포털 API (국민연금공단_국민연금 가입사업장내역, dataset 3046071)
기준년월(baseYm)별 데이터 조회.

환경변수: NPS_SERVICE_KEY, DATA_GO_KR_SERVICE_KEY, PUBLICDATA_SERVICE_KEY, SERVICE_KEY
"""

import os
import time
import xml.etree.ElementTree as ET
from typing import Any, Iterator, Optional
import requests


# 2025.5.7 서비스 변경 후 엔드포인트
NPS_BASE_URL = "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2"
# 구버전 (V2 CLIENT_ERROR 시 시도)
NPS_LEGACY_URL = "http://apis.data.go.kr/B552015/NpsBplcInfoInqireService"


def get_service_key() -> str:
    """공공데이터포털 인증키 조회."""
    for key in ("NPS_SERVICE_KEY", "SBIZ_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY", "PUBLICDATA_SERVICE_KEY", "SERVICE_KEY"):
        val = os.getenv(key, "")
        if val:
            return val.strip()
    return ""


def fetch_page(
    base_ym: str,
    page_no: int = 1,
    num_of_rows: int = 1000,
    service_key: Optional[str] = None,
    base_url: str = NPS_BASE_URL,
    lgdong_cd: Optional[str] = None,
) -> dict[str, Any]:
    """
    국민연금 가입사업장 기본정보 1페이지 조회.

    Args:
        base_ym: 기준년월 (YYYYMM, 예: 201512)
        page_no: 페이지 번호
        num_of_rows: 페이지당 행 수
        service_key: API 인증키 (없으면 환경변수 사용)
        base_url: API base URL
        lgdong_cd: 법정동코드 10자리 (예: 1120011400) - 지원 시 해당 동만 조회

    Returns:
        API 응답 dict (JSON 파싱 결과)
    """
    key = service_key or get_service_key()
    if not key:
        raise ValueError("NPS API 인증키가 없습니다. NPS_SERVICE_KEY 또는 DATA_GO_KR_SERVICE_KEY를 설정하세요.")

    # V2: getBassInfoSearchV2, 구버전: getBassInfoSearch
    op = "getBassInfoSearchV2" if "V2" in base_url else "getBassInfoSearch"
    url = f"{base_url.rstrip('/')}/{op}"
    params = {
        "serviceKey": key,
        "baseYm": base_ym,
        "pageNo": str(page_no),
        "numOfRows": str(num_of_rows),
        "type": "json",
    }
    if lgdong_cd:
        params["lgdongCd"] = lgdong_cd
    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        text = resp.text
        if not text or not text.strip():
            raise RuntimeError("API 응답이 비어있습니다.")
        if "<?xml" in text[:100] or text.strip().startswith("<"):
            data = _parse_nps_xml_response(text)
            header = data.get("response", {}).get("header", {})
            if str(header.get("resultCode", "")) == "97":
                return _retry_with_legacy_params(
                    base_ym, page_no, num_of_rows, key, base_url, lgdong_cd
                )
            return data
        try:
            data = resp.json()
            header = data.get("response", data).get("header", data.get("header", {}))
            if str(header.get("resultCode", "")) == "97":
                return _retry_with_legacy_params(
                    base_ym, page_no, num_of_rows, key, base_url, lgdong_cd
                )
            return data
        except ValueError:
            raise RuntimeError(f"NPS API 응답 파싱 실패. 응답: {text[:500]}...")
    except requests.RequestException as e:
        raise RuntimeError(f"NPS API 요청 실패: {e}") from e


def _parse_nps_xml_response(text: str) -> dict:
    """NPS API XML 응답을 JSON과 동일한 구조의 dict로 변환."""
    root = ET.fromstring(text)
    ns = {}  # namespace 제거
    result = {"response": {"header": {}, "body": {"items": {"item": []}, "totalCount": 0}}}
    for h in root.findall(".//header/*"):
        tag = h.tag.split("}")[-1] if "}" in h.tag else h.tag
        if tag and h.text:
            result["response"]["header"][tag] = h.text
    for name in ("totalCount", "totalcount"):
        total = root.find(f".//{name}")
        if total is not None and total.text:
            try:
                result["response"]["body"]["totalCount"] = int(total.text)
            except ValueError:
                pass
            break
    items = []
    for item in root.findall(".//item"):
        row = {}
        for child in item:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag:
                row[tag] = child.text or ""
        if row:
            items.append(row)
    result["response"]["body"]["items"] = {"item": items} if items else {}
    return result


def _retry_with_legacy_params(
    base_ym: str, page_no: int, num_of_rows: int, key: str, base_url: str, lgdong_cd: Optional[str]
) -> dict:
    """구버전 스네이크케이스 파라미터로 재시도. type=xml로 요청 후 파싱."""
    op = "getBassInfoSearchV2" if "V2" in base_url else "getBassInfoSearch"
    url = f"{base_url.rstrip('/')}/{op}"
    params = {
        "serviceKey": key,
        "base_ym": base_ym,
        "pageNo": str(page_no),
        "numOfRows": str(num_of_rows),
        "type": "xml",
    }
    if lgdong_cd:
        params["lgdong_cd"] = lgdong_cd
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    text = resp.text
    if not text:
        raise RuntimeError("재시도 응답이 비어있습니다.")
    if "<?xml" in text[:50] or text.strip().startswith("<"):
        parsed = _parse_nps_xml_response(text)
        if os.getenv("NPS_DEBUG"):
            print(f"[DEBUG] retry XML len={len(text)}, items={len(_extract_items(parsed))}")
        return parsed
    try:
        return resp.json()
    except ValueError:
        raise RuntimeError(f"재시도 응답 파싱 실패: {text[:300]}...")


def _extract_items(data: dict) -> list[dict]:
    """응답에서 items 리스트 추출 (다양한 응답 구조 대응)."""
    body = data.get("response", data).get("body", data)
    items = body.get("items")
    if items is None:
        return []
    if isinstance(items, dict) and "item" in items:
        it = items["item"]
        return [it] if isinstance(it, dict) else it
    return items if isinstance(items, list) else []


def _extract_total(data: dict) -> int:
    """전체 건수 추출."""
    body = data.get("response", data).get("body", data)
    return int(body.get("totalCount", body.get("total", 0)) or 0)


def fetch_all_pages(
    base_ym: str,
    page_size: int = 1000,
    delay: float = 0.5,
    service_key: Optional[str] = None,
    lgdong_cd: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Iterator[dict]:
    """
    해당 baseYm의 전체 데이터 페이지 단위 반환.

    Yields:
        각 페이지의 item dict 리스트
    """
    page_no = 1
    url = base_url or NPS_BASE_URL
    while True:
        data = fetch_page(
            base_ym, page_no=page_no, num_of_rows=page_size,
            service_key=service_key, lgdong_cd=lgdong_cd, base_url=url
        )
        items = _extract_items(data)
        if not items:
            break
        yield items
        total = _extract_total(data)
        if page_no * page_size >= total or len(items) < page_size:
            break
        page_no += 1
        time.sleep(delay)
