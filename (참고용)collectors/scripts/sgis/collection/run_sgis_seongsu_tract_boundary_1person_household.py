"""
SGIS OpenAPI3: 성수동 집계구 경계 + 1인가구 통계 결합 수집

- 집계구 경계: boundary/statsarea.geojson (8자리 행정동별)
- 1인가구 통계: stats/household.json (household_type=A0)
- 결과 저장: data/raw/sgis/sgis_seongsu_tract_boundary_1person_household_YYYYMMDD_HHMMSS/

참조: collectors/docs/sources/sgis/SGIS_OpenAPI_정의서.pdf
  - 36. 집계구경계 (statsarea.geojson)
  - 6. 가구통계 (household.json, 세대구성 1인가구=A0)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from pyproj import Transformer

# 프로젝트 루트
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# dotenv: collectors/.env 또는 framework/.env
try:
    from dotenv import load_dotenv
    for _d in (project_root, project_root.parent):
        _env = _d / ".env"
        if _env.exists():
            load_dotenv(_env)
            break
except Exception:
    pass

# SGIS OpenAPI3 (통계청)
OPENAPI3_BASE = "https://sgisapi.kostat.go.kr/OpenAPI3"

# 성수동 행정동 8자리 코드 (성동구)
# 성수1가1동, 성수1가2동, 성수2가1동, 성수2가3동
SEONGSU_ADM_CODES = [
    ("11040650", "성수1가1동"),
    ("11040660", "성수1가2동"),
    ("11040670", "성수2가1동"),
    ("11040680", "성수2가3동"),
]

HOUSEHOLD_TYPE_1PERSON = "A0"  # 세대구성코드표: 1인가구
DEFAULT_YEAR = 2023
REQUEST_TIMEOUT = 60

# SGIS API 좌표계(EPSG:5179) -> GeoJSON 표준(WGS84) 변환용
_TRANSFORMER_5179_TO_4326 = None


def _get_transformer():
    global _TRANSFORMER_5179_TO_4326
    if _TRANSFORMER_5179_TO_4326 is None:
        _TRANSFORMER_5179_TO_4326 = Transformer.from_crs(
            "EPSG:5179", "EPSG:4326", always_xy=True
        )
    return _TRANSFORMER_5179_TO_4326


def _transform_coords(coords, transformer):
    """GeoJSON coordinates 배열을 EPSG:5179 -> WGS84(경위도)로 변환."""
    if isinstance(coords[0], (int, float)):
        # [x, y] -> [lon, lat]
        lon, lat = transformer.transform(coords[0], coords[1])
        return [lon, lat]
    return [_transform_coords(item, transformer) for item in coords]


def geojson_5179_to_wgs84(geojson_dict: dict) -> dict:
    """FeatureCollection 내 모든 geometry 좌표를 5179 -> WGS84로 변환."""
    transformer = _get_transformer()
    for feat in geojson_dict.get("features") or []:
        geom = feat.get("geometry")
        if geom and geom.get("coordinates") is not None:
            geom["coordinates"] = _transform_coords(
                geom["coordinates"], transformer
            )
    return geojson_dict


def get_access_token() -> str:
    """SGIS OpenAPI3 액세스 토큰 발급."""
    consumer_key = os.getenv("SGIS_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("SGIS_CONSUMER_SECRET", "").strip()
    if not consumer_key or not consumer_secret:
        raise RuntimeError(
            "SGIS OpenAPI3 인증 정보가 없습니다. .env에 SGIS_CONSUMER_KEY, SGIS_CONSUMER_SECRET 을 설정하세요."
        )
    url = f"{OPENAPI3_BASE}/auth/authentication.json"
    r = requests.get(
        url,
        params={"consumer_key": consumer_key, "consumer_secret": consumer_secret},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errCd") != 0:
        raise RuntimeError(f"SGIS 인증 실패: {data.get('errMsg', data)}")
    return data["result"]["accessToken"]


def fetch_boundary_geojson(access_token: str, adm_cd: str) -> dict:
    """집계구 경계 GeoJSON (해당 행정동 내 모든 집계구)."""
    url = f"{OPENAPI3_BASE}/boundary/statsarea.geojson"
    r = requests.get(
        url,
        params={"accessToken": access_token, "adm_cd": adm_cd},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def fetch_household_1person(access_token: str, adm_cd: str, year: int = DEFAULT_YEAR) -> dict:
    """1인가구 통계 (행정동 또는 집계구 단위)."""
    url = f"{OPENAPI3_BASE}/stats/household.json"
    r = requests.get(
        url,
        params={
            "accessToken": access_token,
            "year": year,
            "adm_cd": adm_cd,
            "household_type": HOUSEHOLD_TYPE_1PERSON,
            "low_search": 0,
        },
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def fetch_household_1person_low_search_2(
    access_token: str, adm_cd_8: str, year: int = DEFAULT_YEAR
) -> dict:
    """1인가구 통계 2단계 하위(집계구) 요청. 8자리 행정동 코드 사용."""
    url = f"{OPENAPI3_BASE}/stats/household.json"
    r = requests.get(
        url,
        params={
            "accessToken": access_token,
            "year": year,
            "adm_cd": adm_cd_8,
            "household_type": HOUSEHOLD_TYPE_1PERSON,
            "low_search": 2,
        },
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def collect_household_1person_by_tract(
    access_token: str,
    all_features: list,
    year: int = DEFAULT_YEAR,
    delay_sec: float = 0.15,
) -> dict:
    """
    집계구별 1인가구 수 수집.
    먼저 8자리 동 단위로 low_search=2 호출로 집계구 목록·통계를 받고,
    불가 시 각 집계구 adm_cd로 개별 호출.
    반환: { tract_adm_cd: { household_cnt, ... }, ... }
    """
    import time
    tract_codes = set()
    for feat in all_features:
        adm = feat.get("properties") or {}
        ac = str(adm.get("adm_cd", "")).strip()
        if len(ac) > 8:
            tract_codes.add(ac)
    if not tract_codes:
        return {}

    # 1) 8자리 동별로 low_search=2 호출 시도 (한 번에 여러 집계구 반환되는지)
    household_by_tract = {}
    dong_codes = set(ac[:8] for ac in tract_codes if len(ac) >= 8)
    for adm8 in sorted(dong_codes):
        try:
            data = fetch_household_1person_low_search_2(access_token, adm8, year)
            if data.get("errCd") != 0:
                continue
            for row in data.get("result") or []:
                ac = str(row.get("adm_cd", "")).strip()
                if len(ac) > 8 and ac in tract_codes:
                    household_by_tract[ac] = {
                        "household_cnt": row.get("household_cnt"),
                        "family_member_cnt": row.get("family_member_cnt"),
                        "avg_family_member_cnt": row.get("avg_family_member_cnt"),
                        "adm_nm": row.get("adm_nm"),
                    }
            time.sleep(delay_sec)
        except Exception:
            continue

    missing = tract_codes - set(household_by_tract.keys())
    if not missing:
        return household_by_tract

    # 2) 미수집 집계구는 집계구 코드로 개별 호출
    for tract_cd in sorted(missing):
        try:
            data = fetch_household_1person(access_token, tract_cd, year)
            if data.get("errCd") != 0:
                continue
            result_list = data.get("result") or []
            if result_list:
                row = result_list[0]
                household_by_tract[tract_cd] = {
                    "household_cnt": row.get("household_cnt"),
                    "family_member_cnt": row.get("family_member_cnt"),
                    "avg_family_member_cnt": row.get("avg_family_member_cnt"),
                    "adm_nm": row.get("adm_nm"),
                }
            time.sleep(delay_sec)
        except Exception:
            continue
    return household_by_tract


def merge_boundary_with_household(
    all_features: list,
    household_by_tract: dict,
    fallback_by_adm8: dict = None,
) -> dict:
    """
    집계구 경계 features에 집계구별 1인가구 수 결합.
    household_by_tract: 집계구 adm_cd(전체) 기준 딕셔너리.
    fallback_by_adm8: 없으면 행정동(8자리) 통계로 보간용.
    """
    for feat in all_features:
        props = feat.get("properties") or {}
        adm_cd_full = str(props.get("adm_cd", "") or "").strip()
        adm8 = adm_cd_full[:8] if len(adm_cd_full) >= 8 else ""
        if adm_cd_full in household_by_tract:
            stats = household_by_tract[adm_cd_full]
            props["household_1person_cnt"] = stats.get("household_cnt")
            props["household_1person_family_member_cnt"] = stats.get("family_member_cnt")
            props["household_1person_avg_member"] = stats.get("avg_family_member_cnt")
            props["household_1person_adm_nm"] = stats.get("adm_nm")
        elif fallback_by_adm8 and adm8 in fallback_by_adm8:
            stats = fallback_by_adm8[adm8]
            props["household_1person_cnt"] = stats.get("household_cnt")
            props["household_1person_family_member_cnt"] = stats.get("family_member_cnt")
            props["household_1person_avg_member"] = stats.get("avg_family_member_cnt")
            props["household_1person_adm_nm"] = stats.get("adm_nm")
        else:
            props["household_1person_cnt"] = None
            props["household_1person_family_member_cnt"] = None
            props["household_1person_avg_member"] = None
            props["household_1person_adm_nm"] = None
    return {
        "type": "FeatureCollection",
        "features": all_features,
    }


def main():
    print("=" * 60)
    print("SGIS OpenAPI3: 성수동 집계구 경계 + 1인가구 통계 수집")
    print("=" * 60)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"sgis_seongsu_tract_boundary_1person_household_{ts}"
    raw_base = project_root / "data" / "raw" / "sgis"
    out_dir = raw_base / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n저장 폴더: {out_dir}")

    try:
        print("\n[1/4] 액세스 토큰 발급 중...")
        token = get_access_token()
        print("[OK] 토큰 발급 완료")

        print("\n[2/4] 집계구 경계 수집 중...")
        all_features = []
        for adm_cd, adm_nm in SEONGSU_ADM_CODES:
            geo = fetch_boundary_geojson(token, adm_cd)
            if geo.get("errCd") != 0:
                print(f"  경고: {adm_nm}({adm_cd}) 집계구 경계 응답 errCd={geo.get('errCd')}")
                continue
            features = geo.get("features") or []
            all_features.extend(features)
            print(f"  - {adm_nm}({adm_cd}): 집계구 {len(features)}개")
        print(f"[OK] 집계구 경계 총 {len(all_features)}개 수집")

        print("\n[3/4] 집계구별 1인가구 통계 수집 중...")
        household_by_tract = collect_household_1person_by_tract(
            token, all_features, year=DEFAULT_YEAR, delay_sec=0.15
        )
        n_fetched = len(household_by_tract)
        print(f"  - 집계구별 수집: {n_fetched}개 / {len(all_features)}개")
        if n_fetched < len(all_features):
            print("  - 미수집 집계구는 행정동 통계로 보간합니다.")
        fallback_by_adm8 = {}
        for adm_cd, adm_nm in SEONGSU_ADM_CODES:
            data = fetch_household_1person(token, adm_cd)
            if data.get("errCd") != 0:
                continue
            result_list = data.get("result") or []
            if result_list:
                row = result_list[0]
                fallback_by_adm8[adm_cd] = {
                    "household_cnt": row.get("household_cnt"),
                    "family_member_cnt": row.get("family_member_cnt"),
                    "avg_family_member_cnt": row.get("avg_family_member_cnt"),
                    "adm_nm": row.get("adm_nm") or adm_nm,
                }
        print("[OK] 1인가구 통계 수집 완료")

        print("\n[4/4] 경계·통계 결합 및 저장 중...")
        merged = merge_boundary_with_household(
            all_features, household_by_tract, fallback_by_adm8=fallback_by_adm8
        )
        # QGIS 등에서 바로 보이도록 좌표계를 WGS84(경위도)로 변환
        merged_wgs84 = geojson_5179_to_wgs84(json.loads(json.dumps(merged)))

        geojson_path = out_dir / "seongsu_tract_boundary_1person_household.geojson"
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(merged_wgs84, f, ensure_ascii=False, indent=2)
        print(f"  - GeoJSON (WGS84): {geojson_path}")

        summary = {
            "folder_name": folder_name,
            "collected_at": ts,
            "year": DEFAULT_YEAR,
            "adm_codes": [{"adm_cd": c, "adm_nm": n} for c, n in SEONGSU_ADM_CODES],
            "tract_count": len(all_features),
            "household_1person_by_tract_count": n_fetched,
            "household_1person_by_tract": household_by_tract,
            "household_1person_by_dong_fallback": fallback_by_adm8,
        }
        summary_path = out_dir / "collection_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  - 요약: {summary_path}")

        # 원본 경계(미결합)도 WGS84로 저장 (QGIS 표시용)
        if all_features:
            raw_geo = {"type": "FeatureCollection", "features": all_features}
            raw_geo_wgs84 = geojson_5179_to_wgs84(
                json.loads(json.dumps(raw_geo))
            )
            raw_geo_path = out_dir / "seongsu_tract_boundary_raw.geojson"
            with open(raw_geo_path, "w", encoding="utf-8") as f:
                json.dump(raw_geo_wgs84, f, ensure_ascii=False, indent=2)
            print(f"  - 원본 경계 (WGS84): {raw_geo_path}")
        with open(out_dir / "seongsu_1person_household_stats_by_tract.json", "w", encoding="utf-8") as f:
            json.dump(household_by_tract, f, ensure_ascii=False, indent=2)
        with open(out_dir / "seongsu_1person_household_stats_by_dong_fallback.json", "w", encoding="utf-8") as f:
            json.dump(fallback_by_adm8, f, ensure_ascii=False, indent=2)
        print(f"  - 집계구별 1인가구: {out_dir / 'seongsu_1person_household_stats_by_tract.json'}")
        print(f"  - 동별 보간용: {out_dir / 'seongsu_1person_household_stats_by_dong_fallback.json'}")

        print("\n" + "=" * 60)
        print("[OK] 모든 작업 완료!")
        print("=" * 60)
        return 0

    except requests.RequestException as e:
        print(f"\n[ERROR] API 요청 오류: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(e.response.text[:500])
            except Exception:
                pass
        return 1
    except Exception as e:
        print(f"\n[ERROR] 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
