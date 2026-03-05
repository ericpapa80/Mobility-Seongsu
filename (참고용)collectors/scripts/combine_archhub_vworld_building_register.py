"""
건축물대장(부속지번) + VWorld 건물 공간 데이터 결합

- ArchHub: bldrgst_getBrAtchJibunInfo (건물별 mgmBldrgstPk, newPlatPlc, bldNm 등)
- VWorld: lt-c-spbd 건물 폴리곤 (pnu, 도로명·건물번호 등)
- 결합: (1) PNU 19자리 [권장] (2) 도로명+본번 (--match-by addr) (3) 캐스케이드 PNU→도로12·본부번→도로명·본번 (--match-by cascade)
- 산출: data/raw/combined/archhub_vworld_building_register_seongsu_{ts}/ 결합 GeoJSON

참고: docs/sources/건축hub/활용및결합방안.md 6.2 결합 키 및 전략
      docs/sources/VWorld_ArchHub_건물데이터_결합방안.md
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _normalize_road(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", "", str(s).strip())


def _norm_road_12(sig_cd: str, rn_cd: str) -> str:
    """VWorld sig_cd + rn_cd -> 12자리 도로코드 (rn_cd 7자리 패딩)."""
    sig = (sig_cd or "").strip().zfill(5)
    rn = (rn_cd or "").strip()
    if len(rn) < 7:
        rn = rn.zfill(7)
    elif len(rn) > 7:
        rn = rn[:7]
    return sig + rn


def _norm_bld(main: str, sub: str) -> tuple:
    """건물 본번/부번 정규화 (앞 0 제거, 빈 값은 0)."""
    m = (main or "0").strip().lstrip("0") or "0"
    s = (sub or "0").strip().lstrip("0") or "0"
    return (m, s)


def _build_pnu(sigungu_cd, bjdong_cd, plat_gb_cd, bun, ji) -> str:
    """
    PNU 19자리 생성: 시군구(5) + 법정동(5) + 대지구분(1) + 본번(4) + 부번(4).
    공공데이터 표준 필지고유번호 형식.
    """
    sig = str(sigungu_cd or "").strip().zfill(5)
    bjd = str(bjdong_cd or "").strip().zfill(5)
    gb = str(plat_gb_cd or "0").strip()
    if gb not in ("0", "1", "2"):
        gb = "0"
    bn = str(bun or "0").strip().zfill(4)
    jb = str(ji or "0").strip().zfill(4)
    return sig + bjd + gb + bn + jb


def _normalize_pnu(pnu: str) -> str:
    """VWorld pnu를 19자리 문자열로 정규화."""
    if not pnu:
        return ""
    s = re.sub(r"\s+", "", str(pnu).strip())
    if len(s) == 19:
        return s
    if len(s) > 19:
        return s[:19]
    return s.zfill(19)


def _pnu_flip_land_type(pnu: str) -> list:
    """
    PNU 19자리에서 11번째 자리(대지구분)가 VWorld/ArchHub 간 0 vs 1로 다를 수 있음.
    두 variant 모두 반환해 조회 시 둘 다 시도할 수 있게 함.
    """
    if not pnu or len(pnu) != 19:
        return [pnu] if pnu else []
    mid = pnu[10:11]
    if mid == "0":
        return [pnu, pnu[:10] + "1" + pnu[11:]]
    if mid == "1":
        return [pnu, pnu[:10] + "0" + pnu[11:]]
    return [pnu]


def _parse_new_plat_plc(new_plat_plc: str):
    """
    '서울특별시 성동구 상원10길 14 (성수동1가)' -> ('상원10길', '14')
    """
    if not new_plat_plc:
        return None, None
    s = new_plat_plc.strip()
    # remove prefix "서울특별시 성동구 " and suffix " (성수동...)"
    m = re.match(r"서울특별시\s*성동구\s+(.+?)\s+\(성수", s)
    if not m:
        m = re.match(r"서울특별시\s*성동구\s+(.+)", s)
    if not m:
        return None, None
    part = m.group(1).strip()
    # part is like "상원10길 14" or "왕십리로14길 29"
    parts = part.rsplit(maxsplit=1)
    if len(parts) < 2:
        return _normalize_road(part), None
    road, num = parts[0].strip(), parts[1].strip()
    if num.isdigit():
        return _normalize_road(road), num
    return _normalize_road(part), None


def _vworld_addr_key(props: dict):
    """VWorld feature properties -> (normalized_road, main_bun)."""
    rd = (props.get("rd_nm") or "").strip()
    bld_s = (props.get("bld_s") or "").strip()
    buld_no = (props.get("buld_no") or "").strip()
    main_bun = bld_s or (buld_no.split("-")[0].strip() if buld_no else "")
    return _normalize_road(rd), main_bun


def _vworld_road_bld_key(props: dict):
    """VWorld feature properties -> (road_12, (main, sub)) for 도로12자리+본번·부번 매칭."""
    sig = (props.get("sig_cd") or "").strip()
    rn = (props.get("rn_cd") or "").strip()
    bld_s = (props.get("bld_s") or "").strip()
    bld_e = (props.get("bld_e") or "").strip()
    road_12 = _norm_road_12(sig, rn)
    return road_12, _norm_bld(bld_s, bld_e)


def load_archhub_by_road_bld(archhub_path: Path) -> dict:
    """
    Load ArchHub AtchJibun JSON, dedupe by mgmBldrgstPk, index by (naRoadCd, norm(naMainBun, naSubBun)).
    Returns: { (road_12, (main, sub)): { bldrgst fields... }, ... }
    """
    with open(archhub_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    by_pk = {}
    for it in items:
        pk = it.get("mgmBldrgstPk")
        if pk is None:
            continue
        if pk not in by_pk:
            by_pk[pk] = it
    out = {}
    for it in by_pk.values():
        road = (it.get("naRoadCd") or "").strip()
        main = it.get("naMainBun") or "0"
        sub = it.get("naSubBun") or "0"
        if not road or len(road) != 12:
            continue
        key = (road, _norm_bld(str(main), str(sub)))
        if key not in out:
            out[key] = it
    return out


def load_archhub_by_pnu(archhub_path: Path) -> dict:
    """
    Load ArchHub AtchJibun JSON, index by PNU (19자리).
    대표지번(sigunguCd,bjdongCd,bun,ji) 및 부속지번(atchSigunguCd,atchBjdongCd,atchBun,atchJi) 모두 인덱스.
    Returns: { pnu_19: { bldrgst fields... }, ... }
    """
    with open(archhub_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    out = {}
    seen_pk = set()
    for it in items:
        pk = it.get("mgmBldrgstPk")
        if pk is None:
            continue
        # 대표지번 PNU
        pnu_main = _build_pnu(
            it.get("sigunguCd"),
            it.get("bjdongCd"),
            it.get("platGbCd"),
            it.get("bun"),
            it.get("ji"),
        )
        if pnu_main and len(pnu_main) == 19:
            for p in _pnu_flip_land_type(pnu_main):
                if p not in out:
                    out[p] = it
        # 부속지번 PNU (동일 건물의 다른 필지)
        pnu_atch = _build_pnu(
            it.get("atchSigunguCd"),
            it.get("atchBjdongCd"),
            it.get("atchPlatGbCd"),
            it.get("atchBun"),
            it.get("atchJi"),
        )
        if pnu_atch and len(pnu_atch) == 19:
            for p in _pnu_flip_land_type(pnu_atch):
                if p not in out:
                    out[p] = it
    return out


def load_archhub_by_addr(archhub_path: Path) -> dict:
    """
    Load ArchHub AtchJibun JSON, dedupe by mgmBldrgstPk, index by (road, main_bun).
    Returns: { (road_norm, main_bun): { bldrgst fields... }, ... }
    """
    with open(archhub_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    by_pk = {}
    for it in items:
        pk = it.get("mgmBldrgstPk")
        if pk is None:
            continue
        if pk not in by_pk:
            by_pk[pk] = it
    out = {}
    for it in by_pk.values():
        road, main = _parse_new_plat_plc(it.get("newPlatPlc") or "")
        if road is None:
            continue
        key = (road, main or "")
        if key not in out:
            out[key] = it
        else:
            # keep first; optionally merge atch count
            pass
    return out


# --- 총괄표제부 (getBrRecapTitleInfo) 전용 로더 ---


def load_archhub_recap_by_pnu(recap_path: Path) -> dict:
    """
    Load ArchHub 총괄표제부 JSON, index by PNU (대표지번 1건 per item).
    Returns: { pnu_19: { bldrgst fields... }, ... }
    """
    with open(recap_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    out = {}
    for it in items:
        pnu_main = _build_pnu(
            it.get("sigunguCd"),
            it.get("bjdongCd"),
            it.get("platGbCd"),
            it.get("bun"),
            it.get("ji"),
        )
        if pnu_main and len(pnu_main) == 19:
            for p in _pnu_flip_land_type(pnu_main):
                if p not in out:
                    out[p] = it
    return out


def load_archhub_recap_by_road_bld(recap_path: Path) -> dict:
    """
    Load ArchHub 총괄표제부 JSON, index by (naRoadCd, norm(naMainBun, naSubBun)).
    naRoadCd가 비어 있거나 공백인 건 제외.
    """
    with open(recap_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    out = {}
    for it in items:
        road = (it.get("naRoadCd") or "").strip()
        if not road or len(road) != 12:
            continue
        main = it.get("naMainBun") or "0"
        sub = it.get("naSubBun") or "0"
        key = (road, _norm_bld(str(main), str(sub)))
        if key not in out:
            out[key] = it
    return out


def load_archhub_recap_by_addr(recap_path: Path) -> dict:
    """
    Load ArchHub 총괄표제부 JSON, index by (road, main_bun) from newPlatPlc.
    newPlatPlc가 비어 있거나 공백인 건 제외.
    """
    with open(recap_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    out = {}
    for it in items:
        new_plat = (it.get("newPlatPlc") or "").strip()
        if not new_plat:
            continue
        road, main = _parse_new_plat_plc(new_plat)
        if road is None:
            continue
        key = (road, main or "")
        if key not in out:
            out[key] = it
    return out


def load_vworld_geojson(geojson_path: Path, filter_sig_cd: str = "11200"):
    """Load VWorld GeoJSON and optionally filter by sig_cd (성동구)."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    features = data.get("features") or []
    if filter_sig_cd:
        features = [f for f in features if (f.get("properties") or {}).get("sig_cd") == filter_sig_cd]
    return features


def combine(
    archhub_path: Path,
    vworld_path: Path,
    out_dir: Path,
    filter_sig_cd: str = "11200",
    match_by: str = "pnu",
    use_recap: bool = False,
    use_basis: bool = False,
):
    """
    Join ArchHub (building register) to VWorld (building polygons).
    Each VWorld feature gets properties prefixed with bldrgst_ when matched.

    match_by: "pnu" = PNU 19자리 정확 매칭 (권장). "addr" = 도로명+본번 매칭.
              "cascade" = 1) PNU 2) 도로12자리+본·부번 3) 도로명+본번 순으로 시도.
    use_recap: True면 총괄표제부(getBrRecapTitleInfo) JSON 사용.
    use_basis: True면 기본개요(getBrBasisOulnInfo) JSON 사용. PNU만 매칭 가능(도로/주소 필드 공백).
    """
    vworld_features = load_vworld_geojson(vworld_path, filter_sig_cd=filter_sig_cd)

    if match_by == "cascade":
        if use_basis:
            arch_by_pnu = load_archhub_recap_by_pnu(archhub_path)  # 기본개요도 동일 PNU 구조
            arch_by_road_bld = load_archhub_recap_by_road_bld(archhub_path)  # 기본개요도 naRoadCd·naMainBun·naSubBun 있음
            arch_by_addr = {}
        elif use_recap:
            arch_by_pnu = load_archhub_recap_by_pnu(archhub_path)
            arch_by_road_bld = load_archhub_recap_by_road_bld(archhub_path)
            arch_by_addr = load_archhub_recap_by_addr(archhub_path)
        else:
            arch_by_pnu = load_archhub_by_pnu(archhub_path)
            arch_by_road_bld = load_archhub_by_road_bld(archhub_path)
            arch_by_addr = load_archhub_by_addr(archhub_path)
        matched_pnu = matched_road_bld = matched_addr = 0
        for feat in vworld_features:
            props = feat.get("properties") or {}
            bldrgst = None
            source = None
            # 1) PNU
            pnu = _normalize_pnu(props.get("pnu") or "")
            if pnu and len(pnu) == 19:
                bldrgst = arch_by_pnu.get(pnu)
                if not bldrgst:
                    for p in _pnu_flip_land_type(pnu):
                        bldrgst = arch_by_pnu.get(p)
                        if bldrgst:
                            break
                if bldrgst:
                    source = "pnu"
                    matched_pnu += 1
            # 2) 도로 12자리 + 본·부번
            if not bldrgst:
                key = _vworld_road_bld_key(props)
                bldrgst = arch_by_road_bld.get(key)
                if bldrgst:
                    source = "road_bld"
                    matched_road_bld += 1
            # 3) 도로명 + 본번
            if not bldrgst:
                key = _vworld_addr_key(props)
                bldrgst = arch_by_addr.get(key)
                if bldrgst:
                    source = "addr"
                    matched_addr += 1
            if bldrgst:
                for k, v in bldrgst.items():
                    props["bldrgst_" + k] = v
                props["bldrgst_matched"] = True
                props["bldrgst_match_source"] = source
            else:
                props["bldrgst_matched"] = False
        matched = matched_pnu + matched_road_bld + matched_addr
        arch_index_size = len(arch_by_pnu)
        summary_extra = {
            "matched_pnu": matched_pnu,
            "matched_road_bld": matched_road_bld,
            "matched_addr": matched_addr,
        }
    elif match_by == "pnu":
        if use_basis or use_recap:
            arch_by_pnu = load_archhub_recap_by_pnu(archhub_path)
        else:
            arch_by_pnu = load_archhub_by_pnu(archhub_path)
        arch_index_size = len(arch_by_pnu)
        matched = 0
        summary_extra = {}
        for feat in vworld_features:
            props = feat.get("properties") or {}
            pnu = _normalize_pnu(props.get("pnu") or "")
            bldrgst = None
            if pnu and len(pnu) == 19:
                bldrgst = arch_by_pnu.get(pnu)
                if not bldrgst:
                    for p in _pnu_flip_land_type(pnu):
                        bldrgst = arch_by_pnu.get(p)
                        if bldrgst:
                            break
            if bldrgst:
                for k, v in bldrgst.items():
                    props["bldrgst_" + k] = v
                props["bldrgst_matched"] = True
                matched += 1
            else:
                props["bldrgst_matched"] = False
    else:
        # addr: 도로명+본번 정확 매칭만 (use_basis 시 도로/주소 없음 → 부속지번 로더 호출해도 비어 있음)
        if use_basis:
            arch_by_addr = {}
        else:
            arch_by_addr = load_archhub_recap_by_addr(archhub_path) if use_recap else load_archhub_by_addr(archhub_path)
        arch_index_size = len(arch_by_addr)
        matched = 0
        summary_extra = {}
        for feat in vworld_features:
            props = feat.get("properties") or {}
            key = _vworld_addr_key(props)
            bldrgst = arch_by_addr.get(key)
            if bldrgst:
                for k, v in bldrgst.items():
                    props["bldrgst_" + k] = v
                props["bldrgst_matched"] = True
                matched += 1
            else:
                props["bldrgst_matched"] = False

    fc = {"type": "FeatureCollection", "features": vworld_features}
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "seongsu_building_register_combined.geojson"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)

    summary = {
        "archhub_path": str(archhub_path),
        "archhub_source": "basis" if use_basis else ("recap" if use_recap else "atch"),
        "vworld_path": str(vworld_path),
        "match_by": match_by,
        "vworld_features_total": len(vworld_features),
        "archhub_indexed": arch_index_size,
        "vworld_matched": matched,
        "output_geojson": str(out_path),
        "created_at": datetime.now().isoformat(),
        **summary_extra,
    }
    summary_path = out_dir / "combine_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return out_path, summary


def main():
    parser = argparse.ArgumentParser(description="건축물대장 + VWorld 건물 결합 GeoJSON 생성")
    parser.add_argument(
        "--archhub",
        type=str,
        default=None,
        help="경로: bldrgst_getBrAtchJibunInfo JSON (부속지번, 기본: archhub_seongsu 최신 폴더)",
    )
    parser.add_argument(
        "--archhub-recap",
        type=str,
        default=None,
        nargs="?",
        metavar="PATH",
        const="",
        help="총괄표제부로 매칭. PATH 생략 시 archhub_seongsu 최신 폴더의 getBrRecapTitleInfo_*.json 사용.",
    )
    parser.add_argument(
        "--archhub-basis",
        type=str,
        default=None,
        nargs="?",
        metavar="PATH",
        const="",
        help="기본개요로 매칭(PNU만). 건수 최다(33k+). PATH 생략 시 getBrBasisOulnInfo_*.json 사용.",
    )
    parser.add_argument(
        "--vworld",
        type=str,
        default=None,
        help="경로: lt-c-spbd GeoJSON (기본: vworld_seongsu 최신 폴더)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="출력 폴더 (기본: data/raw/combined/archhub_vworld_building_register_seongsu_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument(
        "--match-by",
        type=str,
        choices=("pnu", "addr", "cascade"),
        default="pnu",
        help="매칭 방식: pnu=PNU 19자리, addr=도로명+본번, cascade=PNU→도로12·본부번→도로명·본번 순",
    )
    args = parser.parse_args()

    raw = project_root / "data" / "raw"
    use_recap = args.archhub_recap is not None
    use_basis = args.archhub_basis is not None
    if use_recap and use_basis:
        print("[ERROR] --archhub-recap 와 --archhub-basis 는 동시에 지정할 수 없습니다.")
        return 1

    if use_recap:
        if args.archhub_recap:
            archhub_path = Path(args.archhub_recap)
        else:
            arch_dir = raw / "archhub"
            candidates = sorted(arch_dir.glob("archhub_seongsu_*"), key=lambda p: p.name, reverse=True)
            if not candidates:
                print("[ERROR] archhub_seongsu_* 폴더 없음. --archhub-recap PATH 로 파일 지정하세요.")
                return 1
            j = candidates[0] / "bldrgst_getBrRecapTitleInfo_11200_seongsu_20260127_152635.json"
            if not j.exists():
                j = list(candidates[0].glob("bldrgst_getBrRecapTitleInfo_*.json"))
                j = j[0] if j else None
            archhub_path = j
            if not archhub_path or not archhub_path.exists():
                print(f"[ERROR] 총괄표제부 JSON 없음: {candidates[0]}")
                return 1
    elif use_basis:
        if args.archhub_basis:
            archhub_path = Path(args.archhub_basis)
        else:
            arch_dir = raw / "archhub"
            candidates = sorted(arch_dir.glob("archhub_seongsu_*"), key=lambda p: p.name, reverse=True)
            if not candidates:
                print("[ERROR] archhub_seongsu_* 폴더 없음. --archhub-basis PATH 로 파일 지정하세요.")
                return 1
            j = candidates[0] / "bldrgst_getBrBasisOulnInfo_11200_seongsu_20260127_152635.json"
            if not j.exists():
                j = list(candidates[0].glob("bldrgst_getBrBasisOulnInfo_*.json"))
                j = j[0] if j else None
            archhub_path = j
            if not archhub_path or not archhub_path.exists():
                print(f"[ERROR] 기본개요 JSON 없음: {candidates[0]}")
                return 1
    elif args.archhub:
        archhub_path = Path(args.archhub)
    else:
        arch_dir = raw / "archhub"
        candidates = sorted(arch_dir.glob("archhub_seongsu_*"), key=lambda p: p.name, reverse=True)
        if not candidates:
            print("[ERROR] archhub_seongsu_* 폴더 없음. --archhub 로 파일 지정하세요.")
            return 1
        j = candidates[0] / "bldrgst_getBrAtchJibunInfo_11200_seongsu_20260127_152635.json"
        if not j.exists():
            j = list(candidates[0].glob("bldrgst_getBrAtchJibunInfo_*.json"))
            j = j[0] if j else None
        archhub_path = j
        if not archhub_path or not archhub_path.exists():
            print(f"[ERROR] ArchHub JSON 없음: {candidates[0]}")
            return 1

    if args.vworld:
        vworld_path = Path(args.vworld)
    else:
        vw_dir = raw / "vworld"
        candidates = sorted(vw_dir.glob("vworld_seongsu_*"), key=lambda p: p.name, reverse=True)
        if not candidates:
            print("[ERROR] vworld_seongsu_* 폴더 없음. --vworld 로 파일 지정하세요.")
            return 1
        vworld_path = candidates[0] / "seongsu_lt-c-spbd_20260127_134933.geojson"
        if not vworld_path.exists():
            vworld_path = list(candidates[0].glob("seongsu_lt-c-spbd_*.geojson"))
            vworld_path = vworld_path[0] if vworld_path else None
        if not vworld_path or not vworld_path.exists():
            print(f"[ERROR] VWorld GeoJSON 없음: {candidates[0]}")
            return 1

    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = raw / "combined" / f"archhub_vworld_building_register_seongsu_{ts}"

    src_label = "(기본개요)" if use_basis else ("(총괄표제부)" if use_recap else "(부속지번)")
    print("ArchHub:", archhub_path, src_label)
    print("VWorld:", vworld_path)
    print("Output dir:", out_dir)
    print("Match by:", args.match_by)
    out_path, summary = combine(
        archhub_path, vworld_path, out_dir, match_by=args.match_by, use_recap=use_recap, use_basis=use_basis
    )
    print("Written:", out_path)
    print("Matched:", summary["vworld_matched"], "/", summary["vworld_features_total"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
