"""20등분 순차 실행 래퍼 스크립트.

collect_seongsu_hash_to_sales.py를 20등분하여 순차적으로 실행합니다.
모든 분할 결과는 같은 세션 폴더에 저장됩니다.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Windows 콘솔 인코딩 설정 (UTF-8)
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# 프로젝트 루트 경로
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent

def main():
    """20등분 순차 실행 (분할 2부터 시작, 완료 후 병합)."""
    import argparse
    
    parser = argparse.ArgumentParser(description='20등분 순차 수집 (분할 2부터 시작)')
    parser.add_argument('--start-from', type=int, default=2, help='시작 분할 번호 (기본값: 2)')
    parser.add_argument('--session-timestamp', type=str, help='기존 세션 타임스탬프 (예: 20260118_225137)')
    parser.add_argument('--no-merge', action='store_true', help='병합 스크립트 실행 안 함')
    args = parser.parse_args()
    
    print("=" * 80)
    print("20등분 순차 수집 시작")
    print("=" * 80)
    
    # 세션 타임스탬프 (기존 세션 사용 또는 새로 생성)
    if args.session_timestamp:
        session_timestamp = args.session_timestamp
        print(f"기존 세션 사용: {session_timestamp}")
    else:
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"새 세션 생성: {session_timestamp}")
    
    # 메인 스크립트 경로
    main_script = script_dir / "collect_seongsu_hash_to_sales.py"
    
    if not main_script.exists():
        print(f"[ERROR] 스크립트를 찾을 수 없습니다: {main_script}")
        sys.exit(1)
    
    # 20개 분할 순차 실행 (시작 인덱스부터)
    total_splits = 20
    start_index = args.start_from
    successful_splits = 0
    failed_splits = []
    
    print(f"분할 {start_index}부터 {total_splits}까지 실행")
    
    for split_index in range(start_index, total_splits + 1):
        print(f"\n{'=' * 80}")
        print(f"분할 {split_index}/{total_splits} 시작")
        print(f"{'=' * 80}")
        
        # 환경 변수 설정 (세션 타임스탬프 공유 및 인코딩)
        env = os.environ.copy()
        env['SPLIT_SESSION_TIMESTAMP'] = session_timestamp
        env['SPLIT_INDEX'] = str(split_index)
        # Windows에서 UTF-8 출력을 위한 환경 변수
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 실행 명령
        cmd = [
            sys.executable,
            str(main_script),
            '--token-file', '260118_token',
            '--split-index', str(split_index)
        ]
        
        print(f"명령: {' '.join(cmd)}")
        print(f"세션: {session_timestamp}")
        
        try:
            # Python 스크립트 실행 (UTF-8 인코딩으로 출력)
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                env=env,
                check=False,  # 실패해도 계속 진행
                text=True,
                encoding='utf-8',
                errors='replace'  # 인코딩 오류 시 대체 문자 사용
            )
            
            if result.returncode == 0:
                print(f"\n[OK] 분할 {split_index}/{total_splits} 완료")
                successful_splits += 1
            else:
                print(f"\n[FAIL] 분할 {split_index}/{total_splits} 실패 (코드: {result.returncode})")
                failed_splits.append(split_index)
        
        except KeyboardInterrupt:
            print(f"\n\n[WARN] 사용자에 의해 중단되었습니다.")
            print(f"완료된 분할: {successful_splits}/{split_index-1}")
            if failed_splits:
                print(f"실패한 분할: {failed_splits}")
            sys.exit(1)
        
        except Exception as e:
            print(f"\n[FAIL] 분할 {split_index}/{total_splits} 실행 중 오류: {e}")
            failed_splits.append(split_index)
    
    # 최종 리포트
    print(f"\n{'=' * 80}")
    print("20등분 순차 수집 완료")
    print(f"{'=' * 80}")
    print(f"세션: {session_timestamp}")
    print(f"실행된 분할: {start_index}~{total_splits}")
    print(f"성공: {successful_splits}/{total_splits - start_index + 1}")
    if failed_splits:
        print(f"실패: {failed_splits}")
    
    session_dir = project_root / 'data' / 'raw' / 'openup' / f'split_session_{session_timestamp}'
    print(f"\n결과 저장 위치: {session_dir}")
    
    # 분할 20까지 완료되었고 병합 옵션이 활성화되어 있으면 자동 병합
    if not args.no_merge and split_index >= total_splits:
        # 모든 분할이 완료되었는지 확인 (분할 1~20 파일 존재 여부 확인)
        split_files_count = len(list(session_dir.glob("*_split*.json"))) if session_dir.exists() else 0
        
        if split_files_count >= total_splits:
            print(f"\n{'=' * 80}")
            print("분할 20까지 완료되었습니다. 병합 스크립트 실행...")
            print(f"{'=' * 80}")
            
            merge_script = script_dir / "merge_split_collections.py"
            if merge_script.exists():
                try:
                    merge_result = subprocess.run(
                        [sys.executable, str(merge_script), '--session-dir', f'split_session_{session_timestamp}'],
                        cwd=str(project_root),
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )
                    
                    if merge_result.returncode == 0:
                        print("\n[OK] 병합 완료!")
                    else:
                        print(f"\n[WARN] 병합 스크립트가 오류 코드 {merge_result.returncode}로 종료되었습니다.")
                except Exception as e:
                    print(f"\n[ERROR] 병합 스크립트 실행 중 오류: {e}")
                    print(f"수동으로 실행: python {merge_script} --session-dir split_session_{session_timestamp}")
            else:
                print(f"\n[WARN] 병합 스크립트를 찾을 수 없습니다: {merge_script}")
        else:
            print(f"\n[INFO] 아직 모든 분할이 완료되지 않았습니다 (현재 {split_files_count}/{total_splits}개)")
            print(f"모든 분할이 완료되면 다음 명령으로 병합하세요:")
            print(f"  python {script_dir / 'merge_split_collections.py'} --session-dir split_session_{session_timestamp}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
