"""
VWorld (sig_cd, rn_cd, bld_s, bld_e) vs ArchHub (naRoadCd, naMainBun, naSubBun) 조합 비교.

- VWorld 도로: sig_cd(5) + rn_cd(7자리 패딩) = 12자리 (국토부 도로명코드와 동일 체계일 수 있음)
- ArchHub naRoadCd: 12자리 (시군구+도로명코드)
- 건물번호: VWorld (bld_s, bld_e) = 본번-부번 범위/단일, ArchHub (naMainBun, naSubBun) = 단일
"""

import json
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
raw_dir = project_root / "data" / "raw"

VWORLD_GEOJSON = raw_dir / "vworld" / "vworld_seongsu_20260127_134933" / "seongsu_lt-c-spbd_20260127_134933.geojson"
ARCHHUB_JSON = raw_dir / "archhub" / "archhub_seongsu_20260127_152635" / "bldrgst_getBrAtchJibunInfo_11200_seongsu_20260127_152635.json"


def norm_road_12(sig_cd: str, rn_cd: str) -> str:
    """VWorld sig_cd + rn_cd -> 12자리 도로코드 (rn_cd 7자리 패딩)."""
    sig = (sig_cd or "").strip().zfill(5)
    rn = (rn_cd or "").strip()
    if len(rn) < 7:
        rn = rn.zfill(7)
    elif len(rn) > 7:
        rn = rn[:7]
    return sig + rn


def norm_bld(main: str, sub: str) -> tuple:
    """건물 본번/부번 정규화 (앞 0 제거, 빈 값은 0)."""
    m = (main or "0").strip().lstrip("0") or "0"
    s = (sub or "0").strip().lstrip("0") or "0"
    return (m, s)


def main():
    vpath = VWORLD_GEOJSON
    apath = ARCHHUB_JSON
    if len(sys.argv) >= 3:
        vpath = Path(sys.argv[1])
        apath = Path(sys.argv[2])
    if not vpath.exists():
        print(f"VWorld 파일 없음: {vpath}")
        return 1
    if not apath.exists():
        print(f"ArchHub 파일 없음: {apath}")
        return 1

    with open(vpath, "r", encoding="utf-8") as f:
        vworld = json.load(f)
    with open(apath, "r", encoding="utf-8") as f:
        archhub = json.load(f)

    # VWorld: (road_12, bld_s, bld_e) per feature
    vworld_road_bld = set()
    vworld_road_only = set()
    for feat in vworld.get("features", []):
        p = feat.get("properties") or {}
        sig = p.get("sig_cd") or ""
        rn = p.get("rn_cd") or ""
        bld_s = p.get("bld_s") or ""
        bld_e = p.get("bld_e") or ""
        road_12 = norm_road_12(sig, rn)
        vworld_road_only.add(road_12)
        vworld_road_bld.add((road_12, norm_bld(bld_s, bld_e)))

    # ArchHub: unique (naRoadCd, naMainBun, naSubBun)
    arch_road_bld = set()
    arch_road_only = set()
    for item in archhub.get("items", []):
        road = (item.get("naRoadCd") or "").strip()
        main = item.get("naMainBun") or "0"
        sub = item.get("naSubBun") or "0"
        arch_road_only.add(road)
        arch_road_bld.add((road, norm_bld(str(main), str(sub))))

    # 통계
    road_common = vworld_road_only & arch_road_only
    vworld_keys = len(vworld_road_bld)
    arch_keys = len(arch_road_bld)
    # (road_12, (main, sub)) 일치 조합
    match_road_bld = vworld_road_bld & arch_road_bld
    n_match_keys = len(match_road_bld)
    n_vworld_features = len(vworld.get("features", []))

    # VWorld feature 중 (road_12, bld)가 match_road_bld에 포함된 개수
    n_features_matched = sum(
        1 for feat in vworld.get("features", [])
        if (norm_road_12((feat.get("properties") or {}).get("sig_cd") or "", (feat.get("properties") or {}).get("rn_cd") or ""),
             norm_bld((feat.get("properties") or {}).get("bld_s") or "", (feat.get("properties") or {}).get("bld_e") or "")) in match_road_bld
    )

    print("=" * 60)
    print("VWorld (sig_cd, rn_cd, bld_s, bld_e) vs ArchHub (naRoadCd, naMainBun, naSubBun)")
    print("=" * 60)
    print(f"VWorld GeoJSON features: {n_vworld_features}")
    print(f"VWorld unique (road_12, bld_s, bld_e): {vworld_keys}")
    print(f"VWorld unique road_12 (sig_cd+rn_cd): {len(vworld_road_only)}")
    print()
    print(f"ArchHub items: {len(archhub.get('items', []))}")
    print(f"ArchHub unique (naRoadCd, naMainBun, naSubBun): {arch_keys}")
    print(f"ArchHub unique naRoadCd: {len(arch_road_only)}")
    print()
    print(f"Road code 12-digit overlap: {len(road_common)}")
    print(f"(road+main+sub) key match count: {n_match_keys}")
    print(f"VWorld features with matching key: {n_features_matched}")
    if n_vworld_features:
        print(f"  -> Match rate (by feature): {n_features_matched / n_vworld_features * 100:.1f}%")
    print()
    if road_common and n_match_keys:
        print("Sample matching (road_12, (main, sub)):")
        for x in sorted(match_road_bld)[:10]:
            print(f"  {x}")
    print()
    if vworld_road_only and not road_common:
        print("VWorld road_12 sample:")
        for r in sorted(vworld_road_only)[:5]:
            print(f"  {r}")
        print("ArchHub naRoadCd sample:")
        for r in sorted(arch_road_only)[:5]:
            print(f"  {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
