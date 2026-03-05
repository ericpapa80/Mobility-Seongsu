"""
VWorld lt-c-spbd CSV에서 성수동(성수동1가, 성수동2가)만 남기고 나머지 행정동 제거.
"""
import csv
import sys
from pathlib import Path

KEEP_GU = ("성수동1가", "성수동2가")


def main():
    csv_path = Path(
        "collectors/data/raw/vworld/vworld_seongsu_20260127_134933/"
        "seongsu_lt-c-spbd_20260127_134933.csv"
    )
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])

    if not csv_path.exists():
        print("File not found:", csv_path)
        return 1

    print("Loading:", csv_path)
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if "gu" not in (fieldnames or []):
            print("Column 'gu' not found. Columns:", fieldnames)
            return 1
        rows = list(reader)

    total = len(rows)
    filtered = [r for r in rows if (r.get("gu") or "").strip() in KEEP_GU]
    removed = total - len(filtered)

    print("Total rows:", total)
    print("Kept (성수동1가, 성수동2가):", len(filtered))
    print("Removed:", removed)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered)

    print("Written:", csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
