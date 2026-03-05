# -*- coding: utf-8 -*-
"""성수동1가·성수동2가 NPS 연도별 API 수집 (201512 ~ 202412)

국민연금 오픈API를 사용하여 기준년월(baseYm)별로 데이터를 수집하고,
성수동1가·성수동2가만 필터링하여 yearly_seongsu 폴더에 저장합니다.

필수: 공공데이터포털 인증키 (NPS_SERVICE_KEY 또는 DATA_GO_KR_SERVICE_KEY)
"""

import sys
import argparse
import re
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import pandas as pd
from plugins.nps.api_client import get_service_key, fetch_all_pages, NPS_BASE_URL, NPS_LEGACY_URL


def normalize_record(item: dict) -> dict:
    """API 응답 필드를 CSV 컬럼 형식으로 정규화.
    API는 camelCase, CSV는 한글 컬럼명을 사용할 수 있음.
    """
    # 다양한 키 이름 매핑
    def _get(d: dict, *keys):
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return None

    dataDe = _get(item, "dataDe", "data_de", "자료생성년월")
    wkpNm = _get(item, "wkpNm", "wkp_nm", "사업장명")
    bizNo = _get(item, "bizNo", "biz_no", "사업자등록번호")
    joinState = _get(item, "joinState", "join_state", "가입상태")
    addr = _get(item, "addr", "address", "주소")
    ldongAddr = _get(item, "ldongAddr", "ldong_addr", "사업장지번상세주소", "jibunAddr", "jibun_addr")
    ldcCd = _get(item, "ldcCd", "ldc_cd", "고객법정동주소코드", "ldongCd", "ldong_cd")
    sigunguCd = _get(item, "sigunguCd", "sigungu_cd", "시군구코드")
    emdCd = _get(item, "emdCd", "emd_cd", "읍면동코드")
    joinCnt = _get(item, "joinCnt", "join_cnt", "가입자수")
    billAmt = _get(item, "billAmt", "bill_amt", "금액", "당월고지금액")
    newCnt = _get(item, "newCnt", "new_cnt", "신규")
    lostCnt = _get(item, "lostCnt", "lost_cnt", "상실")

    addr_str = str(ldongAddr or addr or "")
    is_seongsu = ("서울" in addr_str or "성동" in addr_str) and (
        "성수동1가" in addr_str or "성수동2가" in addr_str
    )
    if ldcCd:
        # 법정동코드 1120011400(성수동1가), 1120011500(성수동2가)
        ldc_str = str(ldcCd)
        if ldc_str in ("1120011400", "1120011500"):
            is_seongsu = True

    def _int(v):
        if v is None:
            return 0
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return 0

    join_cnt = _int(joinCnt)
    bill_amt = _int(billAmt)
    if join_cnt <= 0:
        join_cnt = 1
    in_per = bill_amt / join_cnt
    month_est = in_per / 9 * 100
    year_est = month_est * 12

    return {
        "자료생성년월": dataDe or "",
        "사업장명": wkpNm or "",
        "사업자등록번호": str(bizNo or ""),
        "가입상태": _int(joinState),
        "사업장지번상세주소": ldongAddr or addr or "",
        "주소": addr or ldongAddr or "",
        "고객법정동주소코드": str(ldcCd or ""),
        "시군구코드": str(sigunguCd or ""),
        "읍면동코드": str(emdCd or ""),
        "가입자수": join_cnt,
        "금액": bill_amt,
        "신규": _int(newCnt),
        "상실": _int(lostCnt),
        "인당금액": in_per,
        "월급여추정": month_est,
        "연간급여추정": year_est,
        "동": "성수동1가" if "성수동1가" in addr_str or str(ldcCd) == "1120011400" else "성수동2가",
        "_is_seongsu": is_seongsu,
    }


def collect_year(base_ym: str, output_dir: Path, page_size: int = 1000, delay: float = 0.5, use_legacy: bool = False) -> int:
    """한 기준년월 데이터 수집 후 성수동만 필터해 CSV 저장. 저장 건수 반환."""
    base_url = NPS_LEGACY_URL if use_legacy else NPS_BASE_URL
    records = []
    for page_items in fetch_all_pages(base_ym, page_size=page_size, delay=delay, base_url=base_url):
        for item in page_items:
            rec = normalize_record(item)
            if rec.get("_is_seongsu"):
                del rec["_is_seongsu"]
                records.append(rec)

    if not records:
        return 0

    df = pd.DataFrame(records)
    yr = base_ym[:4]
    out_file = output_dir / f"nps_seongsu_{yr}.csv"
    df.to_csv(out_file, index=False, encoding="utf-8-sig")
    return len(records)


def main():
    parser = argparse.ArgumentParser(
        description="성수동1가·성수동2가 NPS 연도별 API 수집 (201512~202412)"
    )
    parser.add_argument(
        "--years",
        type=str,
        default="2015,2016,2017,2018,2019,2020,2021,2022,2023,2024",
        help="수집 연도 (쉼표 구분)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="출력 디렉터리 (기본: data/raw/nps/yearly_seongsu)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="API 페이지당 행 수",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="API 호출 간 대기(초)",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="구버전 API(getBassInfoSearch) 사용 (V2 CLIENT_ERROR 시)",
    )
    args = parser.parse_args()

    if not get_service_key():
        print("[오류] NPS API 인증키가 없습니다.")
        print("  환경변수 설정: NPS_SERVICE_KEY 또는 DATA_GO_KR_SERVICE_KEY")
        print("  공공데이터포털(https://www.data.go.kr)에서 '국민연금 가입 사업장 내역' API 활용신청 후 인증키 발급")
        sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else project_root / "data" / "raw" / "nps" / "yearly_seongsu"
    out_dir.mkdir(parents=True, exist_ok=True)

    years = [y.strip() for y in args.years.split(",")]
    base_yms = [f"{y}12" for y in years]

    print("=" * 60)
    print("성수동1가·성수동2가 NPS 연도별 API 수집")
    print("=" * 60)
    print(f"대상: {', '.join(base_yms)}")
    print(f"출력: {out_dir}")
    print()

    for base_ym in base_yms:
        try:
            cnt = collect_year(base_ym, out_dir, args.page_size, args.delay, use_legacy=args.legacy)
            print(f"  {base_ym}: {cnt:,}개 → nps_seongsu_{base_ym[:4]}.csv")
        except Exception as e:
            print(f"  {base_ym}: 오류 - {e}")

    print()
    print("=" * 60)
    print("수집 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
