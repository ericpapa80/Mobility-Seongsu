"""
SGIS Fusion 수집 GUI: accessToken·adm_cd 입력 후
연령(선택), 세대구성(다중), 주택유형(다중), 연면적(선택)을 고르면
앞선 방식으로 연령/ht/ha 컬럼이 생성된 GeoJSON을 sgis_fusion 폴더에 산출.

- 경계: OpenAPI3 boundary/statsarea.geojson (accessToken, adm_cd)
- Fusion: ServiceAPI/fusionstats.json (Cookie/Token은 .env 또는 입력란)
- 컬럼 규칙: 연령 컬럼 = house_type·house_area_cd 없이 호출,
  ht 컬럼 = 연령범위 고정·house_area_cd 없이, ha 컬럼 = 연령범위 고정·house_type 없이.
"""

import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    for _d in (PROJECT_ROOT, PROJECT_ROOT.parent):
        _e = _d / ".env"
        if _e.exists():
            load_dotenv(_e)
            break
except Exception:
    pass

try:
    from pyproj import Transformer
except ImportError:
    Transformer = None

OPENAPI3_BASE = "https://sgisapi.kostat.go.kr/OpenAPI3"
FUSION_URL = "https://sgis.mods.go.kr/ServiceAPI/stats/fusionstats.json"
REFERER = "https://sgis.mods.go.kr/view/map/interactiveMap/populationHouseView"
ORIGIN = "https://sgis.mods.go.kr"
OPENAPI3_TIMEOUT = 60
FUSION_TIMEOUT = 30
DELAY = 0.4
STAT_YEAR = 2024
BND_YEAR = 2025

# 연령 구간 옵션 (from, to, key) — 전연령 선택 가능
AGE_OPTIONS = [
    (0, 9, "0_9"),
    (10, 19, "10_19"),
    (20, 29, "20_29"),
    (30, 39, "30_39"),
    (40, 49, "40_49"),
    (50, 59, "50_59"),
    (60, 69, "60_69"),
    (70, 150, "70+"),
]
HOUSEHOLD_OPTIONS = [
    ("A0", "1인가구"),
    ("01", "1세대가구"),
    ("02", "2세대가구"),
    ("03", "3세대가구"),
    ("04", "4세대가구"),
    ("05", "5세대이상가구"),
    ("B0", "비혈연가구"),
]
HOUSE_TYPE_OPTIONS = [
    ("01", "단독주택"),
    ("02", "아파트"),
    ("03", "연립주택"),
    ("04", "다세대주택"),
    ("05", "비거주용건물내주택"),
    ("06", "주택이외의거처"),
]
# 연면적: 1평≈3.3058㎡ 기준, 문서 9.3 주택면적 코드표
HOUSE_AREA_OPTIONS = [
    ("01", "20㎡이하(약6평이하)"),
    ("02", "20~40㎡(약6~12평)"),
    ("03", "40~60㎡(약12~18평)"),
    ("04", "60~85㎡(약18~26평)"),
    ("05", "85~100㎡(약26~30평)"),
    ("06", "100~130㎡(약30~39평)"),
    ("07", "130~165㎡(약39~50평)"),
    ("08", "165~230㎡(약50~70평)"),
    ("09", "230㎡초과(약70평초과)"),
]

_TRANSFORMER = None

# Fusion 토큰 마지막 입력값 저장 경로 (GUI 재실행 시 그대로 채움)
LAST_FUSION_COOKIE_FILE = PROJECT_ROOT / ".last_fusion_cookie.txt"


def _load_last_fusion_cookie():
    """이전에 입력했던 Fusion Cookie/Token을 읽음."""
    try:
        if LAST_FUSION_COOKIE_FILE.exists():
            return LAST_FUSION_COOKIE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def _save_last_fusion_cookie(value: str):
    """입력한 Fusion Cookie/Token을 저장 (다음 실행 시 채움)."""
    try:
        LAST_FUSION_COOKIE_FILE.write_text(value or "", encoding="utf-8")
    except Exception:
        pass


def _get_transformer():
    global _TRANSFORMER
    if _TRANSFORMER is None and Transformer is not None:
        _TRANSFORMER = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
    return _TRANSFORMER


def _transform_coords(coords, trans):
    if not trans or not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        lon, lat = trans.transform(coords[0], coords[1])
        return [lon, lat]
    return [_transform_coords(c, trans) for c in coords]


def geojson_5179_to_wgs84(gj):
    t = _get_transformer()
    if not t:
        return gj
    for feat in gj.get("features") or []:
        geom = feat.get("geometry")
        if geom and geom.get("coordinates") is not None:
            geom["coordinates"] = _transform_coords(geom["coordinates"], t)
    return gj


def get_boundary_token() -> str:
    """경계 API용 토큰. .env의 SGIS_OPENAPI_ACCESS_TOKEN 또는 CONSUMER_KEY/SECRET으로 발급."""
    token = os.getenv("SGIS_OPENAPI_ACCESS_TOKEN", "").strip()
    if token:
        return token
    key = os.getenv("SGIS_CONSUMER_KEY", "").strip()
    secret = os.getenv("SGIS_CONSUMER_SECRET", "").strip()
    if not key or not secret:
        raise RuntimeError("collectors/.env에 SGIS_OPENAPI_ACCESS_TOKEN 또는 SGIS_CONSUMER_KEY, SGIS_CONSUMER_SECRET 설정 필요")
    r = requests.get(
        f"{OPENAPI3_BASE}/auth/authentication.json",
        params={"consumer_key": key, "consumer_secret": secret},
        timeout=OPENAPI3_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errCd") != 0:
        raise RuntimeError(f"경계 API 인증 실패: {data.get('errMsg', data)}")
    return data["result"]["accessToken"]


def fetch_boundary(token: str, adm_cd: str, year: int = BND_YEAR) -> dict:
    params = {"accessToken": token, "adm_cd": adm_cd.strip()}
    if year is not None:
        params["year"] = year
    r = requests.get(
        f"{OPENAPI3_BASE}/boundary/statsarea.geojson",
        params=params,
        timeout=OPENAPI3_TIMEOUT,
    )
    if r.status_code != 200 and year is not None:
        params = {"accessToken": token, "adm_cd": adm_cd.strip()}
        r = requests.get(
            f"{OPENAPI3_BASE}/boundary/statsarea.geojson",
            params=params,
            timeout=OPENAPI3_TIMEOUT,
        )
    r.raise_for_status()
    return r.json()


def call_fusion(cookie: str, adm_cd: str, params: dict) -> dict:
    ts_ms = datetime.now().strftime("%Y%m%d%H%M%S") + "000"
    payload = {**params, "adm_cd": adm_cd}
    body = "&".join(f"{k}={v}" for k, v in payload.items())
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie,
        "Origin": ORIGIN,
        "Referer": REFERER,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "ts": ts_ms,
    }
    r = requests.post(FUSION_URL, data=body, headers=headers, timeout=FUSION_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _parse_cnt(cnt):
    if cnt is None or cnt == "N/A":
        return None
    if isinstance(cnt, str) and not cnt.strip().isdigit():
        return None
    try:
        return int(cnt)
    except (TypeError, ValueError):
        return None


def _find_zero_runs(ordered_codes, get_val):
    """ordered_codes: 정렬된 코드/키 리스트. get_val(code)->값.
    연속된 0 구간(run)과 그 다음/이전 비영(anchor)을 찾음.
    반환: [(run_codes, anchor_code, anchor_val, 'left'|'right'), ...]
    """
    runs = []
    i = 0
    while i < len(ordered_codes):
        c = ordered_codes[i]
        v = get_val(c)
        if (v or 0) != 0:
            i += 1
            continue
        j = i
        while j < len(ordered_codes) and (get_val(ordered_codes[j]) or 0) == 0:
            j += 1
        run = ordered_codes[i:j]
        # 오른쪽 이웃(비영)이 있으면 right anchor
        if j < len(ordered_codes):
            anchor_code = ordered_codes[j]
            anchor_val = get_val(anchor_code) or 0
            if anchor_val > 0:
                runs.append((run, anchor_code, anchor_val, "right"))
        # 왼쪽 이웃(비영)이 있으면 left anchor (run이 끝까지 갔거나 오른쪽이 없을 때)
        elif i > 0:
            anchor_code = ordered_codes[i - 1]
            anchor_val = get_val(anchor_code) or 0
            if anchor_val > 0:
                runs.append((run, anchor_code, anchor_val, "left"))
        i = j if j < len(ordered_codes) else len(ordered_codes)
    return runs


def _call_sets_for_run(run_codes, anchor_code, anchor_side):
    """한 run에 대해 필요한 결합 호출 set 목록. 각 set은 (정렬된) 코드/키 튜플."""
    if anchor_side == "right":
        # (run 끝, anchor), (run 끝-1, run 끝, anchor), ...
        return [tuple(run_codes[k:]) + (anchor_code,) for k in range(len(run_codes) - 1, -1, -1)]
    else:
        # (anchor, run 처음), (anchor, run 처음~2), ...
        return [tuple([anchor_code] + run_codes[: k + 1]) for k in range(len(run_codes))]


def run_collection(
    access_token: str,
    adm_cd_list: list,
    fusion_cookie: str,
    age_bands: list,
    household_types: list,
    house_types: list,
    house_areas: list,
    include_house: bool,
    log_fn,
):
    """실제 수집·결합. log_fn(msg)로 로그 출력.
    include_house=False 이면 fusion_query_type=population_household, combine_base=household 로 요청(ht/ha 미포함).
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    age_from_global = min(b[0] for b in age_bands) if age_bands else 0
    age_to_global = max(b[1] for b in age_bands) if age_bands else 150
    _hh_code_to_slug = {"A0": "1person", "01": "1gen", "02": "2gen", "03": "3gen", "04": "4gen", "05": "5gen", "B0": "nonfamily"}
    if len(household_types) == 1:
        hh_slug = _hh_code_to_slug.get(household_types[0], household_types[0])
    else:
        hh_slug = "multi"
    run_slug = f"{hh_slug}_{age_from_global}_{age_to_global}"
    out_dir = PROJECT_ROOT / "data" / "raw" / "sgis_fusion" / f"sgis_fusion_{run_slug}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_fn(f"출력 폴더: {out_dir}\n")

    # 1) 경계
    log_fn("[1/4] 집계구 경계 수집...\n")
    all_features = []
    for adm_cd in adm_cd_list:
        adm_cd = adm_cd.strip()
        if not adm_cd:
            continue
        try:
            gj = fetch_boundary(access_token, adm_cd, BND_YEAR)
            feats = gj.get("features") or []
            all_features.extend(feats)
            log_fn(f"  {adm_cd}: {len(feats)}개 집계구\n")
            time.sleep(0.15)
        except Exception as e:
            log_fn(f"  {adm_cd}: 실패 - {e}\n")
    if not all_features:
        log_fn("[ERROR] 경계 수집 실패\n")
        return
    gj_boundary = {"type": "FeatureCollection", "features": all_features}
    gj_boundary = geojson_5179_to_wgs84(gj_boundary)
    with open(out_dir / "boundary_tract.geojson", "w", encoding="utf-8") as f:
        json.dump(gj_boundary, f, ensure_ascii=False, indent=2)
    log_fn(f"  저장: boundary_tract.geojson ({len(all_features)} features)\n\n")

    # 2) Fusion
    log_fn("[2/4] Fusion 결합통계 수집...\n")
    # ht/ha 호출용 대표 세대구성(첫 번째); 연령 컬럼은 세대구성별로 모두 호출
    household_type_for_ht_ha = household_types[0] if household_types else "A0"
    if include_house:
        base_params = {
            "combine_base": "population",
            "household_type": household_type_for_ht_ha,
            "area_type": "0",
            "year": STAT_YEAR,
            "fusion_query_type": "population_household_house",
            "low_search": 1,
            "bnd_year": BND_YEAR,
        }
    else:
        # ht/ha 전체 해제: 인구+가구만 결합 (주택 조건 없음)
        base_params = {
            "combine_base": "household",
            "household_type": household_type_for_ht_ha,
            "area_type": "0",
            "year": STAT_YEAR,
            "fusion_query_type": "population_household",
            "low_search": 1,
            "bnd_year": BND_YEAR,
        }
        house_types = []
        house_areas = []
    # age_lookup: (age_key, tract_cd) -> 인구 수 (연령대별, 선택 세대구성 통합)
    # hh_lookup: (hh_code, tract_cd) -> 인구 수 (세대구성별, 선택 연령 범위 합계)
    age_lookup = {}
    hh_lookup = {}
    ht_lookup = {}
    ha_lookup = {}
    total_requests = 0
    total_errors = 0

    # 1인가구(A0) 단일+주택포함 시에만 오피스텔 추정 플로우
    use_officetel_flow = include_house and len(household_types) == 1 and household_types[0] == "A0"

    # 1) 연령 단독 수집 — age_*, age_total만 요청 (hh/ht/ha 미포함). 이후 age 조건으로 hh/ht/ha 수집.
    # 항상 combine_base=population, fusion_query_type=population_household (주택 조건 없음)
    params_age = {
        "combine_base": "population",
        "fusion_query_type": "population_household",
        "household_type": ",".join(household_types),
        "area_type": "0",
        "year": STAT_YEAR,
        "low_search": 1,
        "bnd_year": BND_YEAR,
    }
    log_fn("  [연령 단독] 연령대별 호출(age_*, age_total) → 이후 동일 연령 조건으로 hh/ht/ha 수집\n")
    for age_from, age_to, age_key in age_bands:
        params = {**params_age, "age_from": age_from, "age_to": age_to}
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            total_requests += 1
            try:
                data = call_fusion(fusion_cookie, adm_cd, params)
                if data.get("errCd") != 0:
                    total_errors += 1
                else:
                    for item in data.get("result") or []:
                        tract_cd = str(item.get("adm_cd", "")).strip()
                        if tract_cd:
                            age_lookup[(age_key, tract_cd)] = _parse_cnt(item.get("data_cnt"))
            except Exception:
                total_errors += 1
            if total_requests % 10 == 0:
                log_fn(f"  진행: {total_requests} 요청 (에러 {total_errors})\n")
            time.sleep(DELAY)

    # 1.2) 세대구성별 hh_* — age 조건(age_from_global~age_to_global) 하에 세대구성별 1회 호출 (hh_code, tract_cd) 저장
    for hh_code in household_types:
        if use_officetel_flow and hh_code == "A0":
            params_hh = {
                "combine_base": "household",
                "household_type": "A0",
                "area_type": "0",
                "year": STAT_YEAR,
                "fusion_query_type": "population_household",
                "low_search": 1,
                "bnd_year": BND_YEAR,
                "age_from": age_from_global,
                "age_to": age_to_global,
            }
        else:
            params_hh = {**base_params, "household_type": hh_code, "age_from": age_from_global, "age_to": age_to_global}
            if not include_house:
                params_hh["combine_base"] = "household"
                params_hh["fusion_query_type"] = "population_household"
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            total_requests += 1
            try:
                data = call_fusion(fusion_cookie, adm_cd, params_hh)
                if data.get("errCd") != 0:
                    total_errors += 1
                else:
                    for item in data.get("result") or []:
                        tract_cd = str(item.get("adm_cd", "")).strip()
                        if tract_cd:
                            hh_lookup[(hh_code, tract_cd)] = _parse_cnt(item.get("data_cnt"))
            except Exception:
                total_errors += 1
            time.sleep(DELAY)

    # 1.5) 가구수 기준 hh_total — age 조건 하에 combine_base=household, 선택 세대구성 쉼표 구분 1회 호출 per adm_cd
    # age_total(인구)와 동일 연령 범위로 가구수 조회해야 인구 >= 가구 관계 유지
    hh_total_lookup = {}  # tract_cd -> 가구수
    params_hht = {
        "combine_base": "household",
        "age_from": age_from_global,
        "age_to": age_to_global,
        "household_type": ",".join(household_types),
        "area_type": "0",
        "year": STAT_YEAR,
        "fusion_query_type": "population_household",
        "low_search": 1,
        "bnd_year": BND_YEAR,
    }
    for adm_cd in adm_cd_list:
        adm_cd = adm_cd.strip()
        if not adm_cd:
            continue
        total_requests += 1
        try:
            data = call_fusion(fusion_cookie, adm_cd, params_hht)
            if data.get("errCd") != 0:
                total_errors += 1
            else:
                for item in data.get("result") or []:
                    tract_cd = str(item.get("adm_cd", "")).strip()
                    if tract_cd:
                        hh_total_lookup[tract_cd] = _parse_cnt(item.get("data_cnt"))
        except Exception:
            total_errors += 1
        time.sleep(DELAY)
    log_fn(f"  가구수 기준 hh_total 요청: {len([a for a in adm_cd_list if a.strip()])}건\n")

    # 2) 주택유형 컬럼 — 연령 범위 고정, house_area_cd 없음
    params_ht = {**base_params, "age_from": age_from_global, "age_to": age_to_global}
    for ht in house_types:
        params = {**params_ht, "house_type": ht}
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            total_requests += 1
            try:
                data = call_fusion(fusion_cookie, adm_cd, params)
                if data.get("errCd") != 0:
                    total_errors += 1
                else:
                    for item in data.get("result") or []:
                        tract_cd = str(item.get("adm_cd", "")).strip()
                        if tract_cd:
                            ht_lookup[(ht, tract_cd)] = _parse_cnt(item.get("data_cnt"))
            except Exception:
                total_errors += 1
            if total_requests % 10 == 0:
                log_fn(f"  진행: {total_requests} 요청 (에러 {total_errors})\n")
            time.sleep(DELAY)

    # 3) 연면적 컬럼 — 연령 범위 고정, house_type 없음
    params_ha = {**base_params, "age_from": age_from_global, "age_to": age_to_global}
    for ha in house_areas:
        params = {**params_ha, "house_area_cd": ha}
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            total_requests += 1
            try:
                data = call_fusion(fusion_cookie, adm_cd, params)
                if data.get("errCd") != 0:
                    total_errors += 1
                else:
                    for item in data.get("result") or []:
                        tract_cd = str(item.get("adm_cd", "")).strip()
                        if tract_cd:
                            ha_lookup[(ha, tract_cd)] = _parse_cnt(item.get("data_cnt"))
            except Exception:
                total_errors += 1
            if total_requests % 10 == 0:
                log_fn(f"  진행: {total_requests} 요청 (에러 {total_errors})\n")
            time.sleep(DELAY)

    log_fn(f"  총 요청: {total_requests}, 에러: {total_errors}\n\n")

    # 3) 결합
    log_fn("[3/4] 경계 + fusion 결합...\n")
    age_keys = [b[2] for b in age_bands]
    age_band_by_key = {b[2]: (b[0], b[1]) for b in age_bands}
    for feat in gj_boundary.get("features") or []:
        props = feat.get("properties") or {}
        tract_cd = str(props.get("adm_cd", "")).strip()
        if not tract_cd:
            continue
        for age_key in age_keys:
            props[f"age_{age_key}"] = age_lookup.get((age_key, tract_cd)) or 0
        for hh_code in household_types:
            props[f"hh_{hh_code}"] = hh_lookup.get((hh_code, tract_cd)) or 0
        props["age_total"] = sum(props.get(f"age_{k}", 0) or 0 for k in age_keys)
        # hh_total = 가구수(combine_base=household 호출 결과). 인구(age_total)와 구분
        props["hh_total"] = hh_total_lookup.get(tract_cd) or 0
        for ht in house_types:
            props[f"ht{ht}"] = ht_lookup.get((ht, tract_cd)) or 0
        for ha in house_areas:
            props[f"ha{ha}"] = ha_lookup.get((ha, tract_cd)) or 0
        props["ht_total"] = sum(props.get(f"ht{ht}", 0) or 0 for ht in house_types)
        props["ha_total"] = sum(props.get(f"ha{ha}", 0) or 0 for ha in house_areas)

    # 3.5) 소수보호 0값 보정: 0인 항목을 인접 항목과 결합 호출해 5 이상이면 차이로 치환
    log_fn("[3.5/4] 0값 보정(결합 호출)...\n")
    # age 보정: (adm_cd, "age", call_set, tract_cd) — 연령만, 세대구성 통합
    combined_lookup = {}
    adm_8_from_tract = lambda tc: tc[:8] if len(tc) >= 8 else tc

    def get_needed_call_sets(features, dim, ordered_codes, key_prefix, key_suffix=None):
        """key_prefix: 'age_', 'hh', 'ht', 'ha'. age 차원은 age_{c} (연령만, key_suffix 미사용)."""
        needed = set()  # set of (adm_8, tuple(call_set))
        for feat in features:
            props = feat.get("properties") or {}
            tract_cd = str(props.get("adm_cd", "")).strip()
            if not tract_cd:
                continue
            adm_8 = adm_8_from_tract(tract_cd)
            if dim == "age":
                def _get(c, p=props):
                    return p.get(f"age_{c}") or 0
            elif dim == "hh":
                def _get(c, p=props):
                    return p.get(f"hh_{c}") or 0
            elif dim == "ht":
                def _get(c, p=props):
                    return p.get(f"ht{c}") or 0
            else:
                def _get(c, p=props):
                    return p.get(f"ha{c}") or 0
            runs = _find_zero_runs(ordered_codes, _get)
            for run_codes, anchor_code, _av, side in runs:
                for call_set in _call_sets_for_run(run_codes, anchor_code, side):
                    needed.add((adm_8, tuple(sorted(call_set))))
        return needed

    # 결합 호출로 보정에 필요한 추가 요청 (연령은 세대구성별로 호출)
    params_ht_global = {**base_params, "age_from": age_from_global, "age_to": age_to_global}
    params_ha_global = {**base_params, "age_from": age_from_global, "age_to": age_to_global}

    if age_keys:
        needed_age = get_needed_call_sets(gj_boundary.get("features") or [], "age", age_keys, "age_")
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            for call_set in {cs for a, cs in needed_age if a == adm_cd}:
                a_from = min(age_band_by_key[k][0] for k in call_set)
                a_to = max(age_band_by_key[k][1] for k in call_set)
                # 연령 보정도 age 단독 요청( population_household )으로 일관
                params = {
                    **params_age,
                    "age_from": a_from,
                    "age_to": a_to,
                }
                total_requests += 1
                try:
                    data = call_fusion(fusion_cookie, adm_cd, params)
                    if data.get("errCd") != 0:
                        total_errors += 1
                    else:
                        for item in data.get("result") or []:
                            tract_cd = str(item.get("adm_cd", "")).strip()
                            if tract_cd:
                                combined_lookup[(adm_cd, "age", call_set, tract_cd)] = _parse_cnt(item.get("data_cnt")) or 0
                except Exception:
                    total_errors += 1
                if total_requests % 10 == 0:
                    log_fn(f"  보정 요청: {total_requests} (에러 {total_errors})\n")
                time.sleep(DELAY)

    if house_types:
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            needed_ht = get_needed_call_sets(gj_boundary.get("features") or [], "ht", house_types, "ht")
            for call_set in {cs for a, cs in needed_ht if a == adm_cd}:
                params = {**params_ht_global, "house_type": ",".join(call_set)}
                total_requests += 1
                try:
                    data = call_fusion(fusion_cookie, adm_cd, params)
                    if data.get("errCd") != 0:
                        total_errors += 1
                    else:
                        for item in data.get("result") or []:
                            tract_cd = str(item.get("adm_cd", "")).strip()
                            if tract_cd:
                                combined_lookup[(adm_cd, "ht", call_set, tract_cd)] = _parse_cnt(item.get("data_cnt")) or 0
                except Exception:
                    total_errors += 1
                if total_requests % 10 == 0:
                    log_fn(f"  보정 요청: {total_requests} (에러 {total_errors})\n")
                time.sleep(DELAY)

    if house_areas:
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            needed_ha = get_needed_call_sets(gj_boundary.get("features") or [], "ha", house_areas, "ha")
            for call_set in {cs for a, cs in needed_ha if a == adm_cd}:
                params = {**params_ha_global, "house_area_cd": ",".join(call_set)}
                total_requests += 1
                try:
                    data = call_fusion(fusion_cookie, adm_cd, params)
                    if data.get("errCd") != 0:
                        total_errors += 1
                    else:
                        for item in data.get("result") or []:
                            tract_cd = str(item.get("adm_cd", "")).strip()
                            if tract_cd:
                                combined_lookup[(adm_cd, "ha", call_set, tract_cd)] = _parse_cnt(item.get("data_cnt")) or 0
                except Exception:
                    total_errors += 1
                if total_requests % 10 == 0:
                    log_fn(f"  보정 요청: {total_requests} (에러 {total_errors})\n")
                time.sleep(DELAY)

    # hh(세대구성) 0값 보정: 0 run + 인접 비영과 결합 호출 후 차이로 0 보정 (선택 연령 범위)
    if len(household_types) >= 2:
        params_hh_global = {
            "combine_base": "population",
            "area_type": "0",
            "year": STAT_YEAR,
            "fusion_query_type": "population_household",
            "low_search": 1,
            "bnd_year": BND_YEAR,
            "age_from": age_from_global,
            "age_to": age_to_global,
        }
        if not include_house:
            params_hh_global["combine_base"] = "household"
        for adm_cd in adm_cd_list:
            adm_cd = adm_cd.strip()
            if not adm_cd:
                continue
            needed_hh = get_needed_call_sets(gj_boundary.get("features") or [], "hh", household_types, "hh")
            for call_set in {cs for a, cs in needed_hh if a == adm_cd}:
                params = {**params_hh_global, "household_type": ",".join(call_set)}
                total_requests += 1
                try:
                    data = call_fusion(fusion_cookie, adm_cd, params)
                    if data.get("errCd") != 0:
                        total_errors += 1
                    else:
                        for item in data.get("result") or []:
                            tract_cd = str(item.get("adm_cd", "")).strip()
                            if tract_cd:
                                combined_lookup[(adm_cd, "hh", call_set, tract_cd)] = _parse_cnt(item.get("data_cnt")) or 0
                except Exception:
                    total_errors += 1
                if total_requests % 10 == 0:
                    log_fn(f"  보정 요청(hh): {total_requests} (에러 {total_errors})\n")
                time.sleep(DELAY)

    # 보정 적용: 각 tract의 0 run에 대해 결합값으로 역산 후 치환 (연령은 age_*만, hh는 세대구성 차원)
    for feat in gj_boundary.get("features") or []:
        props = feat.get("properties") or {}
        tract_cd = str(props.get("adm_cd", "")).strip()
        if not tract_cd:
            continue
        adm_8 = adm_8_from_tract(tract_cd)

        # 연령: 0 run 보정 (age_{key}만, 세대구성 통합)
        get_val = lambda c: props.get(f"age_{c}") or 0
        set_val = lambda c, v: props.__setitem__(f"age_{c}", v)
        runs = _find_zero_runs(age_keys, get_val)
        for run_codes, anchor_code, anchor_val, side in runs:
            call_sets = _call_sets_for_run(run_codes, anchor_code, side)
            corrected = {}
            if side == "right":
                for idx, call_set in enumerate(call_sets):
                    call_set_key = tuple(sorted(call_set))
                    comb = combined_lookup.get((adm_8, "age", call_set_key, tract_cd))
                    if comb is None:
                        continue
                    code_to_fill = run_codes[len(run_codes) - 1 - idx]
                    already = sum(corrected.get(run_codes[j], 0) for j in range(len(run_codes) - idx, len(run_codes)))
                    val = (comb or 0) - already - anchor_val
                    val = max(0, val)
                    corrected[code_to_fill] = val
                    set_val(code_to_fill, val)
            else:
                for idx, call_set in enumerate(call_sets):
                    call_set_key = tuple(sorted(call_set))
                    comb = combined_lookup.get((adm_8, "age", call_set_key, tract_cd))
                    if comb is None:
                        continue
                    code_to_fill = run_codes[idx]
                    already = sum(corrected.get(run_codes[j], 0) for j in range(idx))
                    val = (comb or 0) - already - anchor_val
                    val = max(0, val)
                    corrected[code_to_fill] = val
                    set_val(code_to_fill, val)

        # hh(세대구성): 0 run + 인접 비영 결합 호출값으로 0 보정
        if len(household_types) >= 2:
            get_val = lambda c: props.get(f"hh_{c}") or 0
            set_val = lambda c, v: props.__setitem__(f"hh_{c}", v)
            runs = _find_zero_runs(household_types, get_val)
            for run_codes, anchor_code, anchor_val, side in runs:
                call_sets = _call_sets_for_run(run_codes, anchor_code, side)
                corrected = {}
                if side == "right":
                    for idx, call_set in enumerate(call_sets):
                        call_set_key = tuple(sorted(call_set))
                        comb = combined_lookup.get((adm_8, "hh", call_set_key, tract_cd))
                        if comb is None:
                            continue
                        code_to_fill = run_codes[len(run_codes) - 1 - idx]
                        already = sum(corrected.get(run_codes[j], 0) for j in range(len(run_codes) - idx, len(run_codes)))
                        val = (comb or 0) - already - anchor_val
                        val = max(0, val)
                        corrected[code_to_fill] = val
                        set_val(code_to_fill, val)
                else:
                    for idx, call_set in enumerate(call_sets):
                        call_set_key = tuple(sorted(call_set))
                        comb = combined_lookup.get((adm_8, "hh", call_set_key, tract_cd))
                        if comb is None:
                            continue
                        code_to_fill = run_codes[idx]
                        already = sum(corrected.get(run_codes[j], 0) for j in range(idx))
                        val = (comb or 0) - already - anchor_val
                        val = max(0, val)
                        corrected[code_to_fill] = val
                        set_val(code_to_fill, val)

        for dim, ordered_codes in [("ht", house_types), ("ha", house_areas)]:
            if not ordered_codes:
                continue
            if dim == "ht":
                get_val = lambda c: props.get(f"ht{c}") or 0
                set_val = lambda c, v: props.__setitem__(f"ht{c}", v)
            else:
                get_val = lambda c: props.get(f"ha{c}") or 0
                set_val = lambda c, v: props.__setitem__(f"ha{c}", v)

            runs = _find_zero_runs(ordered_codes, get_val)
            for run_codes, anchor_code, anchor_val, side in runs:
                call_sets = _call_sets_for_run(run_codes, anchor_code, side)
                corrected = {}
                if side == "right":
                    for idx, call_set in enumerate(call_sets):
                        call_set_key = tuple(sorted(call_set))
                        comb = combined_lookup.get((adm_8, dim, call_set_key, tract_cd))
                        if comb is None:
                            continue
                        code_to_fill = run_codes[len(run_codes) - 1 - idx]
                        already = sum(corrected.get(run_codes[j], 0) for j in range(len(run_codes) - idx, len(run_codes)))
                        val = (comb or 0) - already - anchor_val
                        val = max(0, val)
                        corrected[code_to_fill] = val
                        set_val(code_to_fill, val)
                else:
                    for idx, call_set in enumerate(call_sets):
                        call_set_key = tuple(sorted(call_set))
                        comb = combined_lookup.get((adm_8, dim, call_set_key, tract_cd))
                        if comb is None:
                            continue
                        code_to_fill = run_codes[idx]
                        already = sum(corrected.get(run_codes[j], 0) for j in range(idx))
                        val = (comb or 0) - already - anchor_val
                        val = max(0, val)
                        corrected[code_to_fill] = val
                        set_val(code_to_fill, val)

    # age_total / ht_total / ha_total 재계산 (보정 반영). hh_*, hh_total은 API/보정 결과 유지
    for feat in gj_boundary.get("features") or []:
        props = feat.get("properties") or {}
        if props:
            props["age_total"] = sum(props.get(f"age_{k}", 0) or 0 for k in age_keys)
            tract_cd = str(props.get("adm_cd", "")).strip()
            if tract_cd:
                props["hh_total"] = hh_total_lookup.get(tract_cd) or 0
            props["ht_total"] = sum(props.get(f"ht{ht}", 0) or 0 for ht in house_types)
            props["ha_total"] = sum(props.get(f"ha{ha}", 0) or 0 for ha in house_areas)

    # 주택포함 시 ht07(오피스텔)·ha10(오피스텔) 추가: hh_total − ht_total = ht07, hh_total − ha_total = ha10
    if include_house:
        log_fn("  오피스텔 추정: ht07 = hh_total − ht_total, ha10 = hh_total − ha_total\n")
        for feat in gj_boundary.get("features") or []:
            props = feat.get("properties") or {}
            if not props:
                continue
            hh_tot = props.get("hh_total") or 0
            ht_sum = sum(props.get(f"ht{ht}", 0) or 0 for ht in house_types)
            ha_sum = sum(props.get(f"ha{ha}", 0) or 0 for ha in house_areas)
            props["ht07"] = max(0, hh_tot - ht_sum)
            props["ha10"] = max(0, hh_tot - ha_sum)
        for feat in gj_boundary.get("features") or []:
            props = feat.get("properties") or {}
            if props:
                props["ht_total"] = sum(props.get(f"ht{ht}", 0) or 0 for ht in house_types) + (props.get("ht07") or 0)
                props["ha_total"] = sum(props.get(f"ha{ha}", 0) or 0 for ha in house_areas) + (props.get("ha10") or 0)

    log_fn(f"  보정 완료. 총 요청: {total_requests}, 에러: {total_errors}\n\n")

    # 4) 저장
    log_fn("[4/4] 최종 GeoJSON 저장...\n")
    out_geojson = out_dir / f"tract_{run_slug}.geojson"
    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(gj_boundary, f, ensure_ascii=False, indent=2)
    _hh_labels = dict(HOUSEHOLD_OPTIONS)
    _age_lbl = lambda k: "70세 이상" if k == "70+" else (k.replace("_", "~") + "세")
    legend = {
        "age_total": "연령 합계 (선택 연령대 인구 합, combine_base=population)",
        "hh_total": "세대구성 합계 (선택 연령 범위·선택 세대구성 가구수 합, combine_base=household, age_total과 동일 연령)",
        "household_type_codes": "A0=1인가구, 01=1세대가구, 02=2세대가구, 03=3세대가구, 04=4세대가구, 05=5세대이상가구, B0=비혈연가구 (hh_total 호출 시 선택 코드를 쉼표로 나열 예: 01,02,03,04,A0,B0)",
        "ht_total": "주택유형 합계 (검증용)",
        "ha_total": "연면적 합계 (검증용)",
    }
    for _, _, k in age_bands:
        legend[f"age_{k}"] = _age_lbl(k)
    for hh_code in household_types:
        legend[f"hh_{hh_code}"] = f"{_hh_labels.get(hh_code, hh_code)} 합계"
    for code, label in HOUSE_TYPE_OPTIONS:
        if code in house_types:
            legend[f"ht{code}"] = label
    if include_house:
        legend["ht07"] = "오피스텔(추정)"
    for code, label in HOUSE_AREA_OPTIONS:
        if code in house_areas:
            legend[f"ha{code}"] = label
    if include_house:
        legend["ha10"] = "오피스텔(추정)"
    with open(out_dir / "legend.json", "w", encoding="utf-8") as f:
        json.dump(legend, f, ensure_ascii=False, indent=2)
    # GUI에서 체크한 항목을 라벨과 함께 명기
    _ht_labels = dict(HOUSE_TYPE_OPTIONS)
    _ha_labels = dict(HOUSE_AREA_OPTIONS)
    def _age_label(b):
        return "70세 이상" if b[2] == "70+" else f"{b[0]}~{b[1]}세"
    gui_selection = {
        "age_bands": [{"from": b[0], "to": b[1], "key": b[2], "label": _age_label(b)} for b in age_bands],
        "household_types": [{"code": c, "label": _hh_labels.get(c, c)} for c in household_types],
        "house_types": [{"code": c, "label": _ht_labels.get(c, c)} for c in house_types],
        "house_areas": [{"code": c, "label": _ha_labels.get(c, c)} for c in house_areas],
    }
    meta = {
        "collected_at": ts,
        "run_slug": run_slug,
        "stat_year": STAT_YEAR,
        "bnd_year": BND_YEAR,
        "access_token_used": bool(access_token),
        "adm_cd_list": adm_cd_list,
        "gui_selection": gui_selection,
        "age_bands": [{"from": b[0], "to": b[1], "key": b[2]} for b in age_bands],
        "include_house": include_house,
        "officetel_estimate_applied": use_officetel_flow,
        "household_type_for_ht_ha": household_type_for_ht_ha,
        "household_types": household_types,
        "house_types": house_types,
        "house_areas": house_areas,
        "total_requests": total_requests,
        "total_errors": total_errors,
        "zero_correction_applied": True,
        "output_geojson": str(out_geojson),
    }
    with open(out_dir / "collection_summary.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log_fn(f"  최종 GeoJSON: {out_geojson}\n")
    log_fn(f"  범례: {out_dir / 'legend.json'}\n")
    log_fn("[OK] 수집·결합 완료\n")


def main_gui():
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox
    except ImportError:
        print("tkinter 없음. Python 설치 시 tcl/tk 포함 여부 확인.")
        return 1

    root = tk.Tk()
    root.title("SGIS Fusion 수집 (경계 + 결합통계)")
    root.geometry("720x680")
    root.resizable(True, True)

    # 입력 (경계 API 토큰은 collectors/.env에만 저장, env_template.txt 형식)
    f_input = ttk.LabelFrame(root, text="입력", padding=8)
    f_input.pack(fill=tk.X, padx=8, pady=4)
    ttk.Label(f_input, text="adm_cd (8자리, 쉼표 구분):").grid(row=0, column=0, sticky=tk.W, pady=2)
    var_adm = tk.StringVar(value="11040650,11040660,11040670,11040680")
    entry_adm = ttk.Entry(f_input, textvariable=var_adm, width=60)
    entry_adm.grid(row=0, column=1, sticky=tk.EW, padx=4, pady=2)
    ttk.Label(f_input, text="Fusion Cookie/Token (입력값은 다음 실행 시 유지):").grid(row=1, column=0, sticky=tk.W, pady=2)
    var_cookie = tk.StringVar(value=_load_last_fusion_cookie())
    entry_cookie = ttk.Entry(f_input, textvariable=var_cookie, width=60, show="*")
    entry_cookie.grid(row=1, column=1, sticky=tk.EW, padx=4, pady=2)
    f_input.columnconfigure(1, weight=1)

    # 연령 (활성화 체크 시에만 하위 항목 선택 가능)
    f_age = ttk.LabelFrame(root, padding=8)
    f_age.pack(fill=tk.X, padx=8, pady=4)
    var_include_age = tk.BooleanVar(value=True)
    row_age_title = ttk.Frame(f_age)
    row_age_title.pack(fill=tk.X)
    ttk.Label(row_age_title, text="연령 (선택)").pack(side=tk.LEFT)
    ttk.Checkbutton(row_age_title, variable=var_include_age).pack(side=tk.LEFT, padx=(8, 0))
    f_age_grid = ttk.Frame(f_age)
    f_age_grid.pack(fill=tk.X, pady=(4, 0))
    var_ages = {}
    age_widgets = []
    for i, (a_from, a_to, key) in enumerate(AGE_OPTIONS):
        var_ages[key] = tk.BooleanVar(value=(key in ("20_29", "30_39", "40_49")))
        lbl = f"{a_from}~{a_to}세" if key != "70+" else "70세 이상"
        w = ttk.Checkbutton(f_age_grid, text=lbl, variable=var_ages[key])
        w.grid(row=i // 4, column=i % 4, sticky=tk.W, padx=4)
        age_widgets.append(w)
    f_age_grid.columnconfigure(3, weight=1)

    def _sync_age_state(*a):
        state = tk.NORMAL if var_include_age.get() else tk.DISABLED
        for w in age_widgets:
            w.configure(state=state)

    var_include_age.trace_add("write", _sync_age_state)
    _sync_age_state()

    # 세대구성 (활성화 체크 시에만 하위 항목 선택 가능)
    f_hh = ttk.LabelFrame(root, padding=8)
    f_hh.pack(fill=tk.X, padx=8, pady=4)
    var_include_hh = tk.BooleanVar(value=True)
    row_hh_title = ttk.Frame(f_hh)
    row_hh_title.pack(fill=tk.X)
    ttk.Label(row_hh_title, text="세대구성 (다중선택)").pack(side=tk.LEFT)
    ttk.Checkbutton(row_hh_title, variable=var_include_hh).pack(side=tk.LEFT, padx=(8, 0))
    f_hh_grid = ttk.Frame(f_hh)
    f_hh_grid.pack(fill=tk.X, pady=(4, 0))
    var_hh = {}
    hh_widgets = []
    for i, (code, label) in enumerate(HOUSEHOLD_OPTIONS):
        var_hh[code] = tk.BooleanVar(value=(code == "A0"))
        w = ttk.Checkbutton(f_hh_grid, text=label, variable=var_hh[code])
        w.grid(row=i // 4, column=i % 4, sticky=tk.W, padx=4)
        hh_widgets.append(w)
    f_hh_grid.columnconfigure(3, weight=1)

    def _sync_hh_state(*a):
        state = tk.NORMAL if var_include_hh.get() else tk.DISABLED
        for w in hh_widgets:
            w.configure(state=state)

    var_include_hh.trace_add("write", _sync_hh_state)
    _sync_hh_state()

    # 주택유형 (라벨 우측 체크 해제 시 하위 항목 비활성화, 요청에 house_type 미포함)
    f_ht = ttk.LabelFrame(root, padding=8)
    f_ht.pack(fill=tk.X, padx=8, pady=4)
    var_include_ht = tk.BooleanVar(value=True)
    row_ht_title = ttk.Frame(f_ht)
    row_ht_title.pack(fill=tk.X)
    ttk.Label(row_ht_title, text="주택유형 (다중선택)").pack(side=tk.LEFT)
    ttk.Checkbutton(row_ht_title, variable=var_include_ht).pack(side=tk.LEFT, padx=(8, 0))
    f_ht_grid = ttk.Frame(f_ht)
    f_ht_grid.pack(fill=tk.X, pady=(4, 0))
    var_ht = {}
    ht_widgets = []
    for i, (code, label) in enumerate(HOUSE_TYPE_OPTIONS):
        var_ht[code] = tk.BooleanVar(value=True)
        w = ttk.Checkbutton(f_ht_grid, text=label, variable=var_ht[code])
        w.grid(row=i // 3, column=i % 3, sticky=tk.W, padx=4, pady=1)
        ht_widgets.append(w)
    f_ht_grid.columnconfigure(2, weight=1)

    def _sync_ht_state(*a):
        state = tk.NORMAL if var_include_ht.get() else tk.DISABLED
        for w in ht_widgets:
            w.configure(state=state)

    var_include_ht.trace_add("write", _sync_ht_state)
    _sync_ht_state()

    # 연면적 (라벨 우측 체크 해제 시 하위 항목 비활성화, 요청에 house_area_cd 미포함)
    f_ha = ttk.LabelFrame(root, padding=8)
    f_ha.pack(fill=tk.X, padx=8, pady=4)
    var_include_ha = tk.BooleanVar(value=True)
    row_ha_title = ttk.Frame(f_ha)
    row_ha_title.pack(fill=tk.X)
    ttk.Label(row_ha_title, text="연면적 (선택)").pack(side=tk.LEFT)
    ttk.Checkbutton(row_ha_title, variable=var_include_ha).pack(side=tk.LEFT, padx=(8, 0))
    f_ha_grid = ttk.Frame(f_ha)
    f_ha_grid.pack(fill=tk.X, pady=(4, 0))
    var_ha = {}
    ha_widgets = []
    for i, (code, label) in enumerate(HOUSE_AREA_OPTIONS):
        var_ha[code] = tk.BooleanVar(value=True)
        w = ttk.Checkbutton(f_ha_grid, text=label, variable=var_ha[code])
        w.grid(row=i // 5, column=i % 5, sticky=tk.W, padx=4, pady=1)
        ha_widgets.append(w)
    f_ha_grid.columnconfigure(4, weight=1)

    def _sync_ha_state(*a):
        state = tk.NORMAL if var_include_ha.get() else tk.DISABLED
        for w in ha_widgets:
            w.configure(state=state)

    var_include_ha.trace_add("write", _sync_ha_state)
    _sync_ha_state()

    # 전체 체크 / 전체 해제
    def _check_all():
        var_include_age.set(True)
        var_include_hh.set(True)
        var_include_ht.set(True)
        var_include_ha.set(True)
        for key in var_ages:
            var_ages[key].set(True)
        for code in var_hh:
            var_hh[code].set(True)
        for code in var_ht:
            var_ht[code].set(True)
        for code in var_ha:
            var_ha[code].set(True)

    def _uncheck_all():
        var_include_age.set(True)
        var_include_hh.set(True)
        var_include_ht.set(True)
        var_include_ha.set(True)
        for key in var_ages:
            var_ages[key].set(False)
        for code in var_hh:
            var_hh[code].set(False)
        for code in var_ht:
            var_ht[code].set(False)
        for code in var_ha:
            var_ha[code].set(False)

    f_buttons = ttk.Frame(root)
    f_buttons.pack(fill=tk.X, padx=8, pady=4)
    ttk.Button(f_buttons, text="전체 체크", command=_check_all).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(f_buttons, text="전체 해제", command=_uncheck_all).pack(side=tk.LEFT)

    # 로그
    f_log = ttk.LabelFrame(root, text="로그", padding=4)
    f_log.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
    log_text = scrolledtext.ScrolledText(f_log, height=12, wrap=tk.WORD, state=tk.DISABLED)
    log_text.pack(fill=tk.BOTH, expand=True)

    def log(msg):
        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, msg)
        log_text.see(tk.END)
        log_text.configure(state=tk.DISABLED)
        root.update_idletasks()

    running = threading.Lock()

    def do_run():
        if not running.acquire(blocking=False):
            messagebox.showinfo("알림", "이미 수집 중입니다.")
            return
        try:
            try:
                token = get_boundary_token()
            except RuntimeError as e:
                messagebox.showerror("오류", str(e))
                return
            adm_raw = var_adm.get().strip()
            if not adm_raw:
                messagebox.showerror("오류", "adm_cd를 입력하세요 (쉼표 구분 가능).")
                return
            adm_cd_list = [a.strip() for a in adm_raw.split(",") if a.strip()]
            cookie = var_cookie.get().strip()
            if not cookie:
                cookie = os.getenv("SGIS_FUSION_COOKIE", "").strip()
                if not cookie:
                    token_f = os.getenv("SGIS_FUSION_ACCESS_TOKEN", "").strip()
                    cookie = f"accessToken={token_f}" if token_f else ""
            if not cookie:
                messagebox.showerror("오류", "Fusion Cookie/Token이 없습니다. 입력란에 입력하세요.")
                return
            _save_last_fusion_cookie(var_cookie.get().strip())
            age_bands = [
                (a_from, a_to, key)
                for (a_from, a_to, key) in AGE_OPTIONS
                if var_ages[key].get()
            ]
            if not age_bands:
                messagebox.showerror("오류", "연령을 최소 1개 선택하세요.")
                return
            household_types = [code for code, _ in HOUSEHOLD_OPTIONS if var_hh[code].get()]
            if not household_types:
                messagebox.showerror("오류", "세대구성을 최소 1개 선택하세요.")
                return
            include_ht = var_include_ht.get()
            include_ha = var_include_ha.get()
            include_house = include_ht or include_ha
            house_types = [code for code, _ in HOUSE_TYPE_OPTIONS if var_ht[code].get()] if include_ht else []
            house_areas = [code for code, _ in HOUSE_AREA_OPTIONS if var_ha[code].get()] if include_ha else []
            if include_house and not house_types and not house_areas:
                messagebox.showwarning("경고", "주택유형·연면적 둘 다 비어 있으면 해당 컬럼 없이 진행합니다.")

            def run_in_thread():
                try:
                    run_collection(
                        token,
                        adm_cd_list,
                        cookie,
                        age_bands,
                        household_types,
                        house_types,
                        house_areas,
                        include_house,
                        log,
                    )
                except Exception as e:
                    log(f"[ERROR] {e}\n")
                finally:
                    running.release()

            threading.Thread(target=run_in_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("오류", str(e))
            running.release()

    btn_run = ttk.Button(root, text="수집 실행 (경계 + Fusion → GeoJSON)", command=do_run)
    btn_run.pack(pady=8)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main_gui())
