"""정제된 데이터 확인 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

proc_dir = project_root / "data" / "processed" / "sgis"

if proc_dir.exists():
    files = list(proc_dir.rglob("*"))
    file_list = [f for f in files if f.is_file()]
    total_size = sum(f.stat().st_size for f in file_list)
    
    print("=" * 80)
    print("정제된 데이터 현황")
    print("=" * 80)
    print(f"폴더: {proc_dir}")
    print(f"총 파일 수: {len(file_list)}")
    print(f"총 크기: {total_size / 1024 / 1024:.2f} MB")
    
    if file_list:
        print("\n파일 목록:")
        for f in file_list[:10]:
            print(f"  - {f.relative_to(proc_dir)} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
        if len(file_list) > 10:
            print(f"  ... 외 {len(file_list) - 10}개 파일")
else:
    print("정제된 데이터 폴더가 없습니다.")

print("\n" + "=" * 80)
print("원본 데이터 현황")
print("=" * 80)
raw_dir = project_root / "data" / "raw" / "sgis"
if raw_dir.exists():
    raw_folders = [d for d in raw_dir.iterdir() if d.is_dir() and d.name.startswith("sgis_technical_biz_")]
    print(f"원본 데이터 폴더 수: {len(raw_folders)}")
    print(f"원본 데이터 폴더 예시:")
    for folder in raw_folders[:5]:
        files = list(folder.glob("*.json")) + list(folder.glob("*.csv"))
        total_size = sum(f.stat().st_size for f in files)
        print(f"  - {folder.name} ({len(files)}개 파일, {total_size / 1024 / 1024:.2f} MB)")

print("\n" + "=" * 80)
print("삭제 가능 여부")
print("=" * 80)
if proc_dir.exists() and file_list:
    print("✅ 삭제 가능")
    print("  - 원본 데이터가 있으면 정제된 데이터는 재생성 가능")
    print("  - 정제는 단순 변환이므로 원본에서 언제든 재생성 가능")
    print("  - 디스크 공간 절약 가능")
else:
    print("⚠️ 정제된 데이터가 없거나 이미 삭제된 상태입니다.")
