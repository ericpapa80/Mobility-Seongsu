"""서울시 전체 및 경기도 일부 데이터 수집 (hash -> sales(건물) -> sales(매장) 흐름).

[f12 콘솔과 수집의 흐름].txt 문서를 참고하여:
1. /v2/pro/bd/hash: cellTokens로 건물 목록 조회
2. /v2/pro/bd/sales: rdnu(건물 해시 키)로 건물별 매장 목록 조회
3. /v2/pro/store/sales: storeId로 매장별 상세 매출 데이터 조회
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from datetime import datetime
import time
import json
import os
import argparse
import csv
import io
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Thread, Event
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.openup.api_client import OpenUpAPIClient
from core.logger import get_logger
from core.file_handler import FileHandler
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, force=True)
logger = get_logger(__name__)

# 결과 파일
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = project_root / f"openup_hash_to_sales_result_{RUN_TIMESTAMP}.txt"

def log_and_print(message):
    """로그와 파일 출력을 동시에 수행."""
    logger.info(message)
    print(message, flush=True)
    try:
        with open(result_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
            f.flush()
    except Exception:
        pass

# 20260113 새로운 토큰 파일에서 로드
import re

def load_tokens_from_file(token_filename='260113_token'):
    """토큰 파일에서 access-token과 cell_tokens를 로드."""
    # project_root는 이미 collectors 디렉토리를 가리키므로 "collectors"를 추가하지 않음
    token_file = project_root / "docs" / "sources" / "openup" / "raw" / token_filename
    content = token_file.read_text(encoding='utf-8')
    
    # access-token 추출
    access_token_match = re.search(r'OPENUP_ACCESS_TOKEN\s*=\s*([a-f0-9-]+)', content)
    access_token = access_token_match.group(1) if access_token_match else None
    
    # cell_tokens 추출 (중복 제거)
    tokens = re.findall(r'"([^"]+)"', content)
    unique_tokens = sorted(list(set(tokens)))
    
    return access_token, unique_tokens


def load_last_access_token() -> str:
    """마지막으로 입력한 access-token을 파일에서 로드."""
    last_token_file = project_root / ".openup_last_token"
    if last_token_file.exists():
        try:
            return last_token_file.read_text(encoding='utf-8').strip()
        except Exception:
            pass
    return ""


def save_last_access_token(access_token: str):
    """입력한 access-token을 파일에 저장."""
    last_token_file = project_root / ".openup_last_token"
    try:
        last_token_file.write_text(access_token, encoding='utf-8')
    except Exception:
        pass


def show_token_selection_gui(token_filename='260113_token') -> Optional[Tuple[str, List[str]]]:
    """GUI 창을 통해 access-token과 cell-tokens를 선택/입력받는 함수.
    
    Returns:
        (access_token, selected_tokens) 튜플 또는 None (취소 시)
    """
    if not GUI_AVAILABLE:
        print("⚠️ GUI 기능을 사용할 수 없습니다. tkinter가 설치되어 있지 않습니다.")
        return None
    
    # 토큰 파일에서 access-token과 전체 cell-tokens 로드 (기본값으로 사용)
    file_access_token = ""
    all_tokens = []
    try:
        file_access_token, all_tokens = load_tokens_from_file(token_filename)
    except Exception as e:
        # 파일이 없거나 읽을 수 없어도 GUI는 계속 진행 (사용자가 직접 입력 가능)
        pass
    
    # 마지막으로 입력한 access-token 로드 (우선순위: 마지막 입력 > 파일)
    last_access_token = load_last_access_token()
    default_access_token = last_access_token if last_access_token else file_access_token
    
    selected_tokens = []
    final_access_token = ""
    
    # GUI 창 생성
    root = tk.Tk()
    root.title("OpenUp Token 설정")
    root.geometry("750x700")
    root.resizable(True, True)
    
    # Access-token 입력 필드
    access_token_var = tk.StringVar(value=default_access_token)
    
    # 선택 모드 변수
    selection_mode = tk.StringVar(value="all")  # all, custom, manual
    
    def on_mode_change():
        """선택 모드 변경 시 UI 업데이트"""
        mode = selection_mode.get()
        if mode == "all":
            listbox.config(state=tk.DISABLED)
            manual_entry.config(state=tk.DISABLED)
            select_all_btn.config(state=tk.NORMAL)
            clear_all_btn.config(state=tk.NORMAL)
        elif mode == "custom":
            listbox.config(state=tk.NORMAL)
            manual_entry.config(state=tk.DISABLED)
            select_all_btn.config(state=tk.NORMAL)
            clear_all_btn.config(state=tk.NORMAL)
        else:  # manual
            listbox.config(state=tk.DISABLED)
            manual_entry.config(state=tk.NORMAL)
            select_all_btn.config(state=tk.DISABLED)
            clear_all_btn.config(state=tk.DISABLED)
    
    def select_all():
        """전체 선택"""
        if selection_mode.get() == "custom":
            listbox.selection_set(0, tk.END)
            update_count()
    
    def clear_all():
        """전체 선택 해제"""
        if selection_mode.get() == "custom":
            listbox.selection_clear(0, tk.END)
            update_count()
    
    def update_count():
        """선택된 토큰 개수 업데이트"""
        if selection_mode.get() == "custom":
            selected = listbox.curselection()
            if all_tokens:
                count_label.config(text=f"선택된 토큰: {len(selected)}개 / 전체: {len(all_tokens)}개")
            else:
                count_label.config(text="토큰 목록을 불러올 수 없습니다.")
        elif selection_mode.get() == "manual":
            manual_text = manual_entry.get("1.0", tk.END).strip()
            # 주석 라인 제외
            tokens = [t.strip() for t in manual_text.split('\n') if t.strip() and not t.strip().startswith('#')]
            count_label.config(text=f"입력된 토큰: {len(tokens)}개")
        else:
            if all_tokens:
                count_label.config(text=f"전체 토큰: {len(all_tokens)}개")
            else:
                count_label.config(text="토큰 목록을 불러올 수 없습니다.")
    
    def on_submit():
        """확인 버튼 클릭 시"""
        nonlocal selected_tokens, final_access_token
        
        # Access-token 검증
        access_token_input = access_token_var.get().strip()
        if not access_token_input:
            messagebox.showwarning("경고", "Access-token을 입력해주세요.")
            return
        
        # Access-token 형식 검증 (UUID 형식: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        import re
        access_token_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(access_token_pattern, access_token_input.lower()):
            messagebox.showwarning("경고", "Access-token 형식이 올바르지 않습니다.\n예: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
            return
        
        final_access_token = access_token_input
        
        # 입력한 access-token 저장
        save_last_access_token(final_access_token)
        
        # Cell-tokens 처리
        mode = selection_mode.get()
        
        if mode == "all":
            if not all_tokens:
                messagebox.showwarning("경고", "사용할 cell-token이 없습니다. 직접 입력 모드를 사용하거나 토큰 파일을 확인해주세요.")
                return
            selected_tokens = all_tokens.copy()
        elif mode == "custom":
            if not all_tokens:
                messagebox.showwarning("경고", "선택할 cell-token이 없습니다. 직접 입력 모드를 사용하거나 토큰 파일을 확인해주세요.")
                return
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("경고", "최소 1개 이상의 토큰을 선택해주세요.")
                return
            selected_tokens = [all_tokens[i] for i in selected_indices]
        else:  # manual
            manual_text = manual_entry.get("1.0", tk.END).strip()
            if not manual_text:
                messagebox.showwarning("경고", "토큰을 입력해주세요.")
                return
            tokens = [t.strip() for t in manual_text.split('\n') if t.strip()]
            # 유효성 검사 (16진수 문자열인지 확인)
            valid_tokens = []
            for token in tokens:
                token_clean = token.strip('"\'')  # 따옴표 제거
                if token_clean and all(c in '0123456789abcdef' for c in token_clean.lower()):
                    valid_tokens.append(token_clean)
                else:
                    messagebox.showwarning("경고", f"유효하지 않은 토큰 형식: {token}")
                    return
            selected_tokens = valid_tokens
        
        if not selected_tokens:
            messagebox.showwarning("경고", "선택된 토큰이 없습니다.")
            return
        
        root.quit()
        root.destroy()
    
    def on_cancel():
        """취소 버튼 클릭 시"""
        nonlocal selected_tokens, final_access_token
        selected_tokens = []
        final_access_token = ""
        root.quit()
        root.destroy()
    
    # 최상단 프레임: Access-token 입력
    access_token_frame = ttk.LabelFrame(root, text="Access-Token", padding=10)
    access_token_frame.pack(fill=tk.X, padx=10, pady=5)
    
    ttk.Label(access_token_frame, text="Access-Token:").pack(anchor=tk.W)
    access_token_entry = ttk.Entry(access_token_frame, textvariable=access_token_var, width=60)
    access_token_entry.pack(fill=tk.X, pady=5)
    ttk.Label(access_token_frame, text="예: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", 
              font=("TkDefaultFont", 8), foreground="gray").pack(anchor=tk.W)
    
    # 상단 프레임: 선택 모드
    mode_frame = ttk.LabelFrame(root, text="Cell-Tokens 선택 모드", padding=10)
    mode_frame.pack(fill=tk.X, padx=10, pady=5)
    
    ttk.Radiobutton(mode_frame, text="전체 토큰 사용", variable=selection_mode, 
                   value="all", command=on_mode_change).pack(anchor=tk.W)
    ttk.Radiobutton(mode_frame, text="목록에서 선택", variable=selection_mode, 
                   value="custom", command=on_mode_change).pack(anchor=tk.W)
    ttk.Radiobutton(mode_frame, text="직접 입력", variable=selection_mode, 
                   value="manual", command=on_mode_change).pack(anchor=tk.W)
    
    # 중간 프레임: 토큰 목록 또는 입력 영역
    content_frame = ttk.Frame(root)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # 목록 박스 (custom 모드용)
    list_frame = ttk.LabelFrame(content_frame, text="Cell-Tokens 목록", padding=5)
    list_frame.pack(fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)
    
    # 토큰 목록 추가
    if all_tokens:
        for i, token in enumerate(all_tokens):
            listbox.insert(tk.END, f"{i+1:4d}. {token}")
    else:
        listbox.insert(tk.END, "토큰 파일을 찾을 수 없거나 토큰이 없습니다.")
        listbox.config(state=tk.DISABLED)
    
    # 직접 입력 영역 (manual 모드용)
    manual_frame = ttk.LabelFrame(content_frame, text="Cell-Tokens 직접 입력 (한 줄에 하나씩)", padding=5)
    manual_frame.pack(fill=tk.BOTH, expand=True)
    
    manual_entry = scrolledtext.ScrolledText(manual_frame, height=12, wrap=tk.WORD)
    manual_entry.pack(fill=tk.BOTH, expand=True)
    if all_tokens:
        manual_entry.insert("1.0", "\n".join(all_tokens[:10]))  # 예시로 처음 10개 표시
    else:
        manual_entry.insert("1.0", "# 예시:\n357b55c4\n357b55cf\n357b55d4")
    
    # 버튼 프레임
    button_frame = ttk.Frame(content_frame)
    button_frame.pack(fill=tk.X, pady=5)
    
    select_all_btn = ttk.Button(button_frame, text="전체 선택", command=select_all)
    select_all_btn.pack(side=tk.LEFT, padx=5)
    
    clear_all_btn = ttk.Button(button_frame, text="전체 해제", command=clear_all)
    clear_all_btn.pack(side=tk.LEFT, padx=5)
    
    # 선택 개수 표시
    if all_tokens:
        count_label = ttk.Label(button_frame, text=f"전체 토큰: {len(all_tokens)}개")
    else:
        count_label = ttk.Label(button_frame, text="토큰 목록을 불러올 수 없습니다.")
    count_label.pack(side=tk.LEFT, padx=20)
    
    # 목록박스 선택 변경 시 카운트 업데이트
    listbox.bind('<<ListboxSelect>>', lambda e: update_count())
    
    # 하단 프레임: 확인/취소 버튼
    bottom_frame = ttk.Frame(root)
    bottom_frame.pack(fill=tk.X, padx=10, pady=10)
    
    ttk.Button(bottom_frame, text="확인", command=on_submit).pack(side=tk.RIGHT, padx=5)
    ttk.Button(bottom_frame, text="취소", command=on_cancel).pack(side=tk.RIGHT)
    
    # 초기 상태 설정
    on_mode_change()
    update_count()
    
    # GUI 실행
    root.mainloop()
    
    if selected_tokens and final_access_token:
        return (final_access_token, selected_tokens)
    else:
        return None

# 명령줄 인자 파싱
parser = argparse.ArgumentParser(description='OpenUp 데이터 수집')
parser.add_argument('--token-file', type=str, default='260118_token', help='토큰 파일명 (기본값: 260118_token)')
parser.add_argument('--split-index', type=int, help='분할 번호 (1-20), 분할 모드일 때 필수')
parser.add_argument('--test', action='store_true', help='테스트 모드 (처음 5개만)')
parser.add_argument('--expanded-csv', action='store_true', help='Expanded CSV 자동 생성 (기본값: True)')
parser.add_argument('--no-expanded-csv', action='store_true', help='Expanded CSV 생성 안 함')
parser.add_argument('--monitor', action='store_true', help='실시간 모니터링 활성화 (별도 스레드)')
parser.add_argument('--gui', action='store_true', help='GUI 창을 통해 cell-tokens 선택/입력')
args = parser.parse_args()

# Expanded CSV 생성 여부 결정
GENERATE_EXPANDED_CSV = args.expanded_csv or not args.no_expanded_csv

# 토큰 로드 (GUI 모드인 경우 GUI에서 선택, 아니면 파일에서 로드)
if args.gui:
    gui_result = show_token_selection_gui(args.token_file)
    if gui_result is None:
        print("❌ GUI에서 취소되었거나 토큰을 선택하지 않았습니다.")
        sys.exit(1)
    NEW_ACCESS_TOKEN, SEOUL_GYEONGGI_CELL_TOKENS_FULL = gui_result
    print(f"✓ GUI에서 {len(SEOUL_GYEONGGI_CELL_TOKENS_FULL)}개 cell-tokens 선택됨")
else:
    NEW_ACCESS_TOKEN, SEOUL_GYEONGGI_CELL_TOKENS_FULL = load_tokens_from_file(args.token_file)

# 분할 수집 설정 (목동 지역은 토큰이 적으므로 기본적으로 비활성화)
# 토큰 파일명에 'mokdong'이 포함되어 있으면 분할 모드 비활성화
SPLIT_MODE = 'mokdong' not in args.token_file.lower() and len(SEOUL_GYEONGGI_CELL_TOKENS_FULL) > 50
SPLIT_COUNT = 20  # 20등분
SPLIT_INDEX = None  # 분할 번호 (1-20, None이면 명령줄 인자에서 받음)

# 분할 번호 설정
if args.split_index:
    SPLIT_INDEX = args.split_index
elif SPLIT_MODE:
    # 환경 변수에서도 확인
    SPLIT_INDEX = int(os.getenv('SPLIT_INDEX', '1'))

# 테스트 모드
TEST_MODE = args.test
TEST_CELL_TOKENS_COUNT = 5

# cell_tokens 처리 (GUI 모드인 경우 선택한 토큰 그대로 사용)
if args.gui:
    # GUI에서 선택한 토큰 그대로 사용 (테스트/분할 모드 무시)
    SEOUL_GYEONGGI_CELL_TOKENS = SEOUL_GYEONGGI_CELL_TOKENS_FULL
    print(f"[GUI MODE] GUI에서 선택한 {len(SEOUL_GYEONGGI_CELL_TOKENS)}개 cell-tokens 사용")
elif TEST_MODE:
    SEOUL_GYEONGGI_CELL_TOKENS = SEOUL_GYEONGGI_CELL_TOKENS_FULL[:TEST_CELL_TOKENS_COUNT]
    print(f"[TEST MODE] 테스트 모드 활성화: {TEST_CELL_TOKENS_COUNT}개 cell_tokens만 사용")
elif SPLIT_MODE and SPLIT_INDEX:
    # 분할 모드: cell_tokens를 10등분
    total_tokens = len(SEOUL_GYEONGGI_CELL_TOKENS_FULL)
    tokens_per_split = total_tokens // SPLIT_COUNT
    start_idx = (SPLIT_INDEX - 1) * tokens_per_split
    end_idx = start_idx + tokens_per_split if SPLIT_INDEX < SPLIT_COUNT else total_tokens
    SEOUL_GYEONGGI_CELL_TOKENS = SEOUL_GYEONGGI_CELL_TOKENS_FULL[start_idx:end_idx]
    print(f"[SPLIT MODE] 분할 {SPLIT_INDEX}/{SPLIT_COUNT}: {start_idx+1}-{end_idx}번째 cell_tokens 사용 ({len(SEOUL_GYEONGGI_CELL_TOKENS)}개)")
else:
    SEOUL_GYEONGGI_CELL_TOKENS = SEOUL_GYEONGGI_CELL_TOKENS_FULL

# 변수명 호환성을 위해 별칭 생성
SEONGSU_CELL_TOKENS = SEOUL_GYEONGGI_CELL_TOKENS

# 병렬 처리 설정 (성능 최적화 - 실패율 고려하여 조정)
MAX_WORKERS_HASH = 20     # cellTokens 배치 병렬 처리 수 (1단계)
MAX_WORKERS_BUILDINGS = 15  # 건물별 매장 목록 조회 동시 요청 수 (3단계) - 실패율 감소를 위해 더 조정
MAX_WORKERS_STORES = 25   # 매장별 상세 매출 데이터 조회 동시 요청 수 (4단계)

# 스레드 안전을 위한 락
print_lock = Lock()

# ============================================================================
# Expanded CSV 변환 함수 (convert_json_to_expanded_csv.py에서 통합)
# ============================================================================

# 메타데이터에서 정의된 배열 필드의 컬럼명 매핑
ARRAY_FIELD_MAPPINGS = {
    # 세대별 매출 (fam)
    'fam': ['미혼', '기혼', '유자녀'],
    
    # 성별/연령대별 매출 (gender)
    'gender_f': ['20대', '30대', '40대', '50대', '60대'],
    'gender_m': ['20대', '30대', '40대', '50대', '60대'],
    
    # 소비자 유형별 매출 (peco)
    'peco': ['개인', '법인', '외국인'],
    
    # 시간대별 매출 (times)
    'times': ['아침', '점심', '오후', '저녁', '밤', '심야', '새벽'],
    
    # 평일/공휴일 매출 (wdwe)
    'wdwe': ['평일', '공휴일'],
    
    # 재방문 빈도 (revfreq)
    'revfreq': ['평일', '공휴일'],
    
    # 요일별 매출 (weekday)
    'weekday': ['월', '화', '수', '목', '금', '토', '일'],
}


def extract_array_fields(store_data: Dict[str, Any]) -> Dict[str, Any]:
    """배열 필드를 개별 컬럼으로 분리합니다.
    
    Args:
        store_data: 매장 데이터 딕셔너리
        
    Returns:
        확장된 딕셔너리 (배열 필드가 개별 컬럼으로 분리됨)
    """
    expanded = {}
    
    # 기본 필드 복사
    expanded['storeId'] = store_data.get('storeId')
    expanded['storeNm'] = store_data.get('storeNm')
    expanded['road_address'] = store_data.get('road_address')
    expanded['site_address'] = store_data.get('site_address')
    expanded['floor'] = store_data.get('floor', '')
    
    # 카테고리 정보
    category = store_data.get('category', {})
    expanded['category_bg'] = category.get('bg', '')
    expanded['category_mi'] = category.get('mi', '')
    expanded['category_sl'] = category.get('sl', '')
    
    # 좌표 정보 (coordinates)
    coordinates = store_data.get('coordinates', [])
    if isinstance(coordinates, list) and len(coordinates) >= 2:
        expanded['x'] = coordinates[0] if coordinates[0] is not None else ''
        expanded['y'] = coordinates[1] if coordinates[1] is not None else ''
    else:
        expanded['x'] = ''
        expanded['y'] = ''
    
    # 매출 데이터 (salesData)
    sales_data = store_data.get('salesData', {})
    
    # fam (세대별 매출)
    fam = sales_data.get('fam', [])
    if isinstance(fam, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['fam']):
            expanded[f'fam_{label}'] = fam[i] if i < len(fam) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['fam']:
            expanded[f'fam_{label}'] = ''
    
    # gender (성별/연령대별 매출)
    gender = sales_data.get('gender', {})
    
    # gender.f (여성)
    gender_f = gender.get('f', [])
    if isinstance(gender_f, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['gender_f']):
            expanded[f'gender_f_{label}'] = gender_f[i] if i < len(gender_f) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['gender_f']:
            expanded[f'gender_f_{label}'] = ''
    
    # gender.m (남성)
    gender_m = gender.get('m', [])
    if isinstance(gender_m, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['gender_m']):
            expanded[f'gender_m_{label}'] = gender_m[i] if i < len(gender_m) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['gender_m']:
            expanded[f'gender_m_{label}'] = ''
    
    # peco (소비자 유형별 매출)
    peco = sales_data.get('peco', [])
    if isinstance(peco, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['peco']):
            expanded[f'peco_{label}'] = peco[i] if i < len(peco) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['peco']:
            expanded[f'peco_{label}'] = ''
    
    # times (시간대별 매출)
    times = sales_data.get('times', [])
    if isinstance(times, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['times']):
            expanded[f'times_{label}'] = times[i] if i < len(times) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['times']:
            expanded[f'times_{label}'] = ''
    
    # wdwe (평일/공휴일 매출)
    wdwe = sales_data.get('wdwe', [])
    if isinstance(wdwe, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['wdwe']):
            expanded[f'wdwe_{label}'] = wdwe[i] if i < len(wdwe) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['wdwe']:
            expanded[f'wdwe_{label}'] = ''
    
    # revfreq (재방문 빈도)
    revfreq = sales_data.get('revfreq', [])
    if isinstance(revfreq, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['revfreq']):
            expanded[f'revfreq_{label}'] = revfreq[i] if i < len(revfreq) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['revfreq']:
            expanded[f'revfreq_{label}'] = ''
    
    # weekday (요일별 매출)
    weekday = sales_data.get('weekday', [])
    if isinstance(weekday, list):
        for i, label in enumerate(ARRAY_FIELD_MAPPINGS['weekday']):
            expanded[f'weekday_{label}'] = weekday[i] if i < len(weekday) else ''
    else:
        for label in ARRAY_FIELD_MAPPINGS['weekday']:
            expanded[f'weekday_{label}'] = ''
    
    return expanded


def convert_stores_to_expanded_csv(stores_data: List[Dict[str, Any]], output_csv_path: Path):
    """매장 데이터를 확장된 CSV로 변환합니다.
    
    Args:
        stores_data: 매장 데이터 리스트
        output_csv_path: 출력 CSV 파일 경로
    """
    log_and_print(f"\n[5-3] Expanded CSV 변환 시작")
    log_and_print(f"  매장 데이터 개수: {len(stores_data)}")
    
    # 각 매장 데이터를 확장된 형식으로 변환
    expanded_data = []
    for store in stores_data:
        expanded = extract_array_fields(store)
        expanded_data.append(expanded)
    
    if not expanded_data:
        log_and_print("  ⚠️ 변환할 데이터가 없습니다.")
        return
    
    # CSV 파일로 저장
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = list(expanded_data[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(expanded_data)
    
    log_and_print(f"  ✓ Expanded CSV 저장: {output_csv_path}")
    log_and_print(f"  ✓ 컬럼 수: {len(fieldnames)}개")


# ============================================================================
# Trend 연도별 컬럼 추가 함수 (add_trend_yearly_to_csv.py에서 통합)
# ============================================================================

def aggregate_trend_by_year(trend_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Trend 데이터를 연도별로 집계합니다.
    
    Args:
        trend_data: trend 배열 데이터
        
    Returns:
        연도별 집계 딕셔너리 {year: {'store': sum, 'delivery': sum, 'cnt': sum}}
    """
    yearly_agg = defaultdict(lambda: {'store': 0, 'delivery': 0, 'cnt': 0})
    
    for item in trend_data:
        if not isinstance(item, dict):
            continue
            
        date_str = item.get('date', '')
        if len(date_str) >= 4:
            year = date_str[:4]
            store = item.get('store', 0) or 0
            delivery = item.get('delivery', 0) or 0
            cnt = item.get('cnt', 0) or 0
            
            yearly_agg[year]['store'] += store
            yearly_agg[year]['delivery'] += delivery
            yearly_agg[year]['cnt'] += cnt
    
    return dict(yearly_agg)


def add_trend_columns_to_expanded_csv(
    csv_path: Path,
    stores_data: List[Dict[str, Any]],
    output_csv_path: Path
):
    """Expanded CSV 파일에 trend 연도별 집계 컬럼을 추가합니다.
    
    Args:
        csv_path: 입력 CSV 파일 경로
        stores_data: 매장 데이터 리스트 (trend 데이터 포함)
        output_csv_path: 출력 CSV 파일 경로
    """
    log_and_print(f"\n[5-4] Trend 연도별 컬럼 추가 시작")
    
    # Trend 데이터를 연도별로 집계
    trend_by_store = {}
    for store in stores_data:
        store_id = store.get('storeId')
        if not store_id:
            continue
            
        trend_data = store.get('trend', [])
        if trend_data:
            yearly_agg = aggregate_trend_by_year(trend_data)
            trend_by_store[store_id] = yearly_agg
    
    if not trend_by_store:
        log_and_print("  ⚠️ Trend 데이터가 없습니다.")
        return
    
    # 모든 연도 추출
    years = set()
    for store_trend in trend_by_store.values():
        years.update(store_trend.keys())
    years = sorted(years)
    
    log_and_print(f"  발견된 연도: {years}")
    log_and_print(f"  Trend 데이터가 있는 매장 수: {len(trend_by_store)}")
    
    # CSV 파일 읽기
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    
    log_and_print(f"  CSV 행 수: {len(rows)}")
    log_and_print(f"  기존 컬럼 수: {len(fieldnames)}")
    
    # 새로운 컬럼명 생성 (연도별로 store, delivery, cnt)
    new_columns = []
    for year in years:
        new_columns.extend([f'{year}_store', f'{year}_deli', f'{year}_cnt'])
    
    # 모든 컬럼명 (기존 + 새로운)
    all_fieldnames = fieldnames + new_columns
    log_and_print(f"  추가될 컬럼 수: {len(new_columns)}")
    log_and_print(f"  최종 컬럼 수: {len(all_fieldnames)}")
    
    # 각 행에 trend 데이터 추가
    for row in rows:
        store_id = row.get('storeId', '')
        if store_id in trend_by_store:
            store_trend = trend_by_store[store_id]
            for year in years:
                year_data = store_trend.get(year, {})
                row[f'{year}_store'] = year_data.get('store', 0)
                row[f'{year}_deli'] = year_data.get('delivery', 0)
                row[f'{year}_cnt'] = year_data.get('cnt', 0)
        else:
            # trend 데이터가 없는 경우 0으로 채움
            for year in years:
                row[f'{year}_store'] = 0
                row[f'{year}_deli'] = 0
                row[f'{year}_cnt'] = 0
    
    # CSV 파일로 저장
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    log_and_print(f"  ✓ Trend 컬럼 추가 완료: {output_csv_path}")
    log_and_print(f"  ✓ 추가된 연도별 컬럼: {', '.join(new_columns[:10])}{'...' if len(new_columns) > 10 else ''}")


# ============================================================================
# 모니터링 함수 (monitor_collection.py에서 통합)
# ============================================================================

def monitor_collection_thread(log_file_path: Path, stop_event):
    """별도 스레드에서 실행되는 모니터링 함수"""
    # Windows 콘솔 인코딩 설정
    if sys.platform == 'win32':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except:
            pass
    
    last_size = 0
    last_line_count = 0
    displayed_lines = set()
    
    while not stop_event.is_set():
        if not log_file_path.exists():
            time.sleep(2)
            continue
        
        try:
            current_size = log_file_path.stat().st_size
            current_mtime = log_file_path.stat().st_mtime
            
            if current_size != last_size:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                current_line_count = len(lines)
                
                # 새로 추가된 라인만 표시
                if current_line_count > last_line_count:
                    new_lines = lines[last_line_count:]
                    for line in new_lines:
                        line_stripped = line.rstrip()
                        if line_stripped and line_stripped not in displayed_lines:
                            if '✓' in line_stripped or '완료' in line_stripped:
                                print(f"[MONITOR] [OK] {line_stripped}")
                            elif '✗' in line_stripped or '실패' in line_stripped:
                                print(f"[MONITOR] [FAIL] {line_stripped}")
                            elif '⚠' in line_stripped:
                                print(f"[MONITOR] [WARN] {line_stripped}")
                            elif '배치' in line_stripped:
                                print(f"[MONITOR] [BATCH] {line_stripped}")
                            displayed_lines.add(line_stripped)
                            if len(displayed_lines) > 1000:
                                displayed_lines = set(list(displayed_lines)[-500:])
                
                last_size = current_size
                last_line_count = current_line_count
        except Exception as e:
            pass
        
        time.sleep(0.5)

def main():
    """메인 실행 함수."""
    # 모니터링 스레드 시작 (옵션)
    monitor_thread = None
    stop_monitor = None
    if args.monitor:
        stop_monitor = Event()
        monitor_thread = Thread(target=monitor_collection_thread, args=(result_file, stop_monitor), daemon=True)
        monitor_thread.start()
        log_and_print("실시간 모니터링 활성화됨")
    
    # 새 토큰 설정
    os.environ['OPENUP_ACCESS_TOKEN'] = NEW_ACCESS_TOKEN
    
    # 지역명 확인 (토큰 파일명에서 추출)
    region_name = "목동" if 'mokdong' in args.token_file.lower() else "서울시 전체 및 경기도 일부"
    
    # 시작 메시지
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"{region_name} 데이터 수집 (hash -> sales(건물) -> sales(매장))\n")
        f.write(f"실행 시간: {datetime.now().isoformat()}\n")
        f.write(f"새로운 access-token: {NEW_ACCESS_TOKEN[:20]}...\n")
        f.write(f"cellTokens: {len(SEOUL_GYEONGGI_CELL_TOKENS)}개 (중복 제거됨)\n")
        f.write("=" * 80 + "\n\n")
        f.flush()
    
    log_and_print("=" * 80)
    if TEST_MODE:
        log_and_print("⚠️ 테스트 모드: 작은 데이터만 수집")
    elif SPLIT_MODE and SPLIT_INDEX:
        log_and_print(f"📦 분할 수집 모드: {SPLIT_INDEX}/{SPLIT_COUNT} 분할")
    log_and_print(f"{region_name} 데이터 수집 시작")
    log_and_print("=" * 80)
    log_and_print(f"새로운 access-token: {NEW_ACCESS_TOKEN[:20]}...")
    log_and_print(f"cellTokens 수: {len(SEOUL_GYEONGGI_CELL_TOKENS)}개 (전체: {len(SEOUL_GYEONGGI_CELL_TOKENS_FULL)}개)")
    if TEST_MODE:
        log_and_print(f"⚠️ 테스트 모드: {TEST_CELL_TOKENS_COUNT}개 cell_tokens만 사용")
    elif SPLIT_MODE and SPLIT_INDEX:
        log_and_print(f"📦 분할 {SPLIT_INDEX}/{SPLIT_COUNT}: {len(SEOUL_GYEONGGI_CELL_TOKENS)}개 cell_tokens 사용")
    
    try:
        # OpenUp API 클라이언트 초기화
        log_and_print("\n[1단계] OpenUp API 클라이언트 초기화")
        openup_client = OpenUpAPIClient()
        log_and_print(f"  ✓ 클라이언트 초기화 완료 (토큰: {openup_client.access_token[:20]}...)")
        
        # 2. cellTokens로 건물 목록 수집 (병렬 처리)
        log_and_print("\n[2단계] /v2/pro/bd/hash - cellTokens로 건물 목록 수집 (병렬 처리)")
        log_and_print(f"동시 요청 수: {MAX_WORKERS_HASH}개")
        all_buildings = {}
        
        batch_size = 10
        
        def fetch_building_hash_batch(batch_data: Tuple[int, List[str]]) -> Tuple[int, Dict[str, Any], bool, Optional[str]]:
            """cellTokens 배치로 건물 목록 조회 (병렬 처리용 함수)."""
            batch_num, batch = batch_data
            # 각 스레드에서 별도의 클라이언트 인스턴스 생성 (thread-safe)
            client = OpenUpAPIClient()
            error_msg = None
            try:
                data = client.get_building_hash(batch)
                if 'bd' in data:
                    buildings = data['bd']
                    client.close()
                    return (batch_num, buildings, True, None)
                else:
                    error_msg = f"No 'bd' key in response"
                    client.close()
                    return (batch_num, {}, False, error_msg)
            except Exception as e:
                error_msg = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    error_msg = f"{type(e).__name__}: {status_code} - {error_msg}"
                else:
                    error_msg = f"{type(e).__name__}: {error_msg}"
                client.close()
                return (batch_num, {}, False, error_msg)
        
        # 배치 생성
        batches = []
        for i in range(0, len(SEOUL_GYEONGGI_CELL_TOKENS), batch_size):
            batch = SEOUL_GYEONGGI_CELL_TOKENS[i:i+batch_size]
            batch_num = i // batch_size + 1
            batches.append((batch_num, batch))
        
        total_batches = len(batches)
        log_and_print(f"총 {total_batches}개 배치를 병렬 처리합니다.")
        
        # 병렬 처리
        completed_batches = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_HASH) as executor:
            future_to_batch = {
                executor.submit(fetch_building_hash_batch, batch_data): batch_data[0]
                for batch_data in batches
            }
            
            for future in as_completed(future_to_batch):
                completed_batches += 1
                batch_num, buildings, success, error_msg = future.result()
                
                with print_lock:
                    if success:
                        all_buildings.update(buildings)
                        log_and_print(f"[{completed_batches}/{total_batches}] 배치 {batch_num}: ✓ {len(buildings)}개 건물 수집")
                    else:
                        error_display = error_msg[:100] if error_msg else "알 수 없는 오류"
                        log_and_print(f"[{completed_batches}/{total_batches}] 배치 {batch_num}: ✗ 실패 - {error_display}")
        
        log_and_print(f"\n총 {len(all_buildings)}개 건물 수집 완료")
        
        # 서울시 전체 및 경기도 일부 건물 필터링
        # 서울시: '서울' 또는 서울시 구 이름 포함
        # 경기도: '경기' 포함하되 일부 지역만 (필요시 추가 필터링)
        target_buildings = {}
        seoul_count = 0
        gyeonggi_count = 0
        
        for bld_key, bld_info in all_buildings.items():
            addr = bld_info.get('ROAD_ADDR', '') or bld_info.get('ADDR', '')
            # 서울시 필터링
            if '서울' in addr or any(gu in addr for gu in ['종로구', '중구', '용산구', '성동구', '광진구', 
                                                           '동대문구', '중랑구', '성북구', '강북구', '도봉구',
                                                           '노원구', '은평구', '서대문구', '마포구', '양천구',
                                                           '강서구', '구로구', '금천구', '영등포구', '동작구',
                                                           '관악구', '서초구', '강남구', '송파구', '강동구']):
                target_buildings[bld_key] = bld_info
                seoul_count += 1
            # 경기도 일부 필터링 (필요시 지역명 추가)
            elif '경기' in addr:
                # 경기도 일부 지역만 포함 (예: 수원, 성남, 고양 등)
                target_buildings[bld_key] = bld_info
                gyeonggi_count += 1
        
        log_and_print(f"서울시 건물: {seoul_count}개")
        log_and_print(f"경기도 건물: {gyeonggi_count}개")
        log_and_print(f"총 대상 건물: {len(target_buildings)}개")
        
        if not target_buildings:
            log_and_print("\n⚠️ 대상 건물이 수집되지 않았습니다.")
            return
        
        # 변수명 호환성
        seongsu_buildings = target_buildings
        
        # 3. 건물별 매장 ID 수집 (/v2/pro/bd/sales with rdnu) - 병렬 처리
        log_and_print("\n[3단계] /v2/pro/bd/sales - 건물별 매장 목록 수집 (병렬 처리)")
        log_and_print("주의: rdnu 파라미터로 건물 해시 키를 사용합니다.")
        log_and_print(f"동시 요청 수: {MAX_WORKERS_BUILDINGS}개")
        
        def fetch_building_stores(bld_item: Tuple[str, Dict[str, Any]]) -> Tuple[str, Dict[str, Any], List[str], bool, Optional[str]]:
            """건물별 매장 목록 조회 (병렬 처리용 함수) - 재시도 로직 포함."""
            bld_key, bld_info = bld_item
            addr = bld_info.get('ROAD_ADDR', 'N/A')
            
            max_retries = 2  # 최대 2번 재시도
            retry_delay = 0.5  # 재시도 간 지연 시간
            
            for attempt in range(max_retries + 1):
                # 각 스레드에서 별도의 클라이언트 인스턴스 생성 (thread-safe)
                client = OpenUpAPIClient()
                error_msg = None
                try:
                    sales_data = client.get_building_sales_by_rdnu(bld_key)
                    
                    # 응답 검증 - 빈 딕셔너리도 유효한 응답으로 처리 (매장이 없는 건물)
                    if sales_data is None:
                        error_msg = f"Invalid response: None"
                        if attempt < max_retries:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            client.close()
                            return (bld_key, bld_info, [], False, error_msg)
                    
                    # dict가 아니면 에러
                    if not isinstance(sales_data, dict):
                        error_msg = f"Invalid response type: {type(sales_data)}"
                        if attempt < max_retries:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            client.close()
                            return (bld_key, bld_info, [], False, error_msg)
                    
                    # 빈 딕셔너리는 매장이 없는 건물로 처리 (성공으로 간주)
                    if not sales_data:
                        client.close()
                        return (bld_key, bld_info, [], True, None)
                    
                    # stores 추출 (안전하게)
                    stores = sales_data.get('stores', [])
                    if not isinstance(stores, list):
                        stores = []
                    
                    store_ids = []
                    for s in stores:
                        if isinstance(s, dict) and s.get('storeId'):
                            store_ids.append(s.get('storeId'))
                    
                    client.close()
                    return (bld_key, bld_info, store_ids, True, None)
                except AttributeError as e:
                    client.close()
                    # AttributeError는 응답 구조 문제일 가능성이 높음
                    error_msg = f"AttributeError: {str(e)} - 응답 구조 문제 가능"
                    # AttributeError는 재시도하지 않음 (데이터 문제)
                    return (bld_key, bld_info, [], False, error_msg)
                except Exception as e:
                    client.close()
                    # 에러 정보 수집
                    error_msg = str(e)
                    status_code = None
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        error_msg = f"{type(e).__name__}: {status_code} - {error_msg}"
                    else:
                        error_msg = f"{type(e).__name__}: {error_msg}"
                    
                    # 재시도 가능한 에러인지 확인
                    should_retry = False
                    if status_code:
                        # 429 (Rate Limit), 500, 502, 503, 504는 재시도
                        if status_code in [429, 500, 502, 503, 504]:
                            should_retry = True
                    else:
                        # 네트워크 에러 등은 재시도
                        if attempt < max_retries:
                            should_retry = True
                    
                    if should_retry and attempt < max_retries:
                        time.sleep(retry_delay * (attempt + 1))  # 지수 백오프
                        continue
                    else:
                        return (bld_key, bld_info, [], False, error_msg)
            
            # 모든 재시도 실패
            return (bld_key, bld_info, [], False, error_msg)
        
        all_store_ids = set()
        success_count = 0
        fail_count = 0
        total_buildings = len(seongsu_buildings)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_BUILDINGS) as executor:
            # 모든 건물에 대한 작업 제출
            future_to_building = {
                executor.submit(fetch_building_stores, item): item[0]
                for item in seongsu_buildings.items()
            }
            
            completed = 0
            # 진행 상황 로깅 간격 조정 (더 자주 표시)
            log_interval = max(1, min(50, total_buildings // 200))  # 최소 50개마다, 최대 200분할
            # 에러 추적
            error_counts = {}
            recent_errors = []
            last_log_time = time.time()
            
            for future in as_completed(future_to_building):
                completed += 1
                bld_key, bld_info, store_ids, success, error_msg = future.result()
                
                if success:
                    if store_ids:
                        all_store_ids.update(store_ids)
                        success_count += 1
                    else:
                        success_count += 1
                else:
                    fail_count += 1
                    # 에러 추적
                    if error_msg:
                        error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg[:30]
                        error_counts[error_type] = error_counts.get(error_type, 0) + 1
                        if len(recent_errors) < 10:
                            recent_errors.append((bld_key[:20], error_msg[:100]))
                
                # 로깅: 간격마다 또는 5초마다 한 번
                current_time = time.time()
                should_log = (completed % log_interval == 0 or 
                             completed == total_buildings or
                             (current_time - last_log_time) >= 5.0)  # 최소 5초마다 한 번
                
                if should_log:
                    addr = bld_info.get('ROAD_ADDR', 'N/A')
                    progress_pct = completed * 100 // total_buildings if total_buildings > 0 else 0
                    with print_lock:
                        log_and_print(f"[{completed}/{total_buildings}] 진행률: {progress_pct}% | 성공: {success_count} | 실패: {fail_count} | 총 storeId: {len(all_store_ids)}")
                        if store_ids:
                            log_and_print(f"  예시: {addr[:50]}... - {len(store_ids)}개 storeId")
                        # 에러 통계 표시 (주기적으로)
                        if error_counts and completed % (log_interval * 10) == 0:
                            log_and_print(f"  주요 에러 유형: {dict(list(error_counts.items())[:3])}")
                    last_log_time = current_time
            
            # 최종 에러 리포트
            if error_counts:
                log_and_print(f"\n[에러 분석] 총 실패: {fail_count}개")
                log_and_print(f"에러 유형별 통계:")
                for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    log_and_print(f"  {error_type}: {count}회")
                if recent_errors:
                    log_and_print(f"\n최근 에러 예시 (최대 5개):")
                    for bld_key, err_msg in recent_errors[:5]:
                        log_and_print(f"  {bld_key}...: {err_msg}")
        
        log_and_print(f"\n건물별 storeId 수집 완료:")
        log_and_print(f"  성공: {success_count}개 건물")
        log_and_print(f"  실패: {fail_count}개 건물")
        log_and_print(f"  총 storeId: {len(all_store_ids)}개")
        
        if not all_store_ids:
            log_and_print("\n⚠️ 매장 ID가 수집되지 않았습니다.")
            return
        
        # 4. 매장별 상세 매출 데이터 수집 - 병렬 처리
        log_and_print("\n[4단계] /v2/pro/store/sales - 매장별 상세 매출 데이터 수집 (병렬 처리)")
        log_and_print(f"동시 요청 수: {MAX_WORKERS_STORES}개")
        
        def fetch_store_sales(store_id: str) -> Tuple[str, Dict[str, Any] | None, bool]:
            """매장별 상세 매출 데이터 조회 (병렬 처리용 함수)."""
            # 각 스레드에서 별도의 클라이언트 인스턴스 생성 (thread-safe)
            client = OpenUpAPIClient()
            try:
                sales = client.get_store_sales(store_id)
                addr = sales.get('road_address', '') or sales.get('site_address', '')
                
                # 서울시 전체 및 경기도 일부 필터링
                is_target = False
                if '서울' in addr or any(gu in addr for gu in ['종로구', '중구', '용산구', '성동구', '광진구', 
                                                               '동대문구', '중랑구', '성북구', '강북구', '도봉구',
                                                               '노원구', '은평구', '서대문구', '마포구', '양천구',
                                                               '강서구', '구로구', '금천구', '영등포구', '동작구',
                                                               '관악구', '서초구', '강남구', '송파구', '강동구']):
                    is_target = True
                elif '경기' in addr:
                    # 경기도 일부 지역만 포함
                    is_target = True
                
                if is_target:
                    # cntPng와 salesPng 필드 제거
                    sales.pop('cntPng', None)
                    sales.pop('salesPng', None)
                    return (store_id, sales, True)
                else:
                    return (store_id, None, False)  # 대상 지역 아님
            except Exception as e:
                return (store_id, None, False)  # 실패
            finally:
                client.close()
        
        # 중복 제거를 위한 set 사용
        seen_store_ids = set()
        sales_data_list = []
        success_sales = 0
        fail_sales = 0
        total_stores = len(all_store_ids)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_STORES) as executor:
            # 모든 매장에 대한 작업 제출
            future_to_store = {
                executor.submit(fetch_store_sales, store_id): store_id
                for store_id in all_store_ids
            }
            
            completed = 0
            # 진행 상황 로깅 간격 조정 (더 자주 표시)
            log_interval = max(1, min(50, total_stores // 200))  # 최소 50개마다, 최대 200분할
            last_log_time = time.time()
            
            for future in as_completed(future_to_store):
                completed += 1
                store_id, sales_data, success = future.result()
                
                if success and sales_data:
                    # 중복 제거: storeId로 중복 확인
                    store_id_key = sales_data.get('storeId') or store_id
                    if store_id_key not in seen_store_ids:
                        seen_store_ids.add(store_id_key)
                        sales_data_list.append(sales_data)
                        success_sales += 1
                    # 중복은 조용히 무시
                else:
                    fail_sales += 1
                
                # 로깅: 간격마다 또는 5초마다 한 번
                current_time = time.time()
                should_log = (completed % log_interval == 0 or 
                             completed == total_stores or
                             (current_time - last_log_time) >= 5.0)  # 최소 5초마다 한 번
                
                if should_log:
                    progress_pct = completed * 100 // total_stores if total_stores > 0 else 0
                    with print_lock:
                        log_and_print(f"[{completed}/{total_stores}] 진행률: {progress_pct}% | 성공: {success_sales} | 실패: {fail_sales} | 총 데이터: {len(sales_data_list)}")
                        if success and sales_data:
                            store_name = sales_data.get('storeNm', 'N/A')
                            log_and_print(f"  예시: {store_name}")
                    last_log_time = current_time
        
        log_and_print(f"\n매장별 매출 데이터 수집 완료:")
        log_and_print(f"  성공: {success_sales}개")
        log_and_print(f"  실패: {fail_sales}개")
        log_and_print(f"  총 데이터: {len(sales_data_list)}개")
        
        # 5. 데이터 저장
        log_and_print("\n[5단계] 데이터 저장")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 분할 모드일 때 세션 폴더 생성 (모든 분할이 같은 세션 폴더에 저장)
        if SPLIT_MODE and SPLIT_INDEX:
            # 세션 시작 시간을 환경 변수에서 가져오거나 새로 생성
            session_timestamp = os.getenv('SPLIT_SESSION_TIMESTAMP', timestamp)
            os.environ['SPLIT_SESSION_TIMESTAMP'] = session_timestamp  # 다음 분할을 위해 저장
            output_dir = project_root / "data" / "raw" / "openup" / f"split_session_{session_timestamp}"
        else:
            output_dir = project_root / "data" / "raw" / "openup" / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 5-1. 건물 데이터 저장
        log_and_print("\n[5-1] 건물 데이터 저장")
        buildings_data_list = []
        for bld_key, bld_info in seongsu_buildings.items():
            center = bld_info.get('center', [])
            # center에서 x, y 좌표 추출
            x = None
            y = None
            if isinstance(center, list) and len(center) >= 2:
                x = float(center[0]) if center[0] is not None else None
                y = float(center[1]) if center[1] is not None else None
            
            building_data = {
                "building_hash": bld_key,
                "road_address": bld_info.get('ROAD_ADDR', ''),
                "address": bld_info.get('ADDR', ''),
                "building_names": bld_info.get('bd_nms', []),
                "decoded_rdnu": bld_info.get('decodedRdnu', ''),
                "marker_point": bld_info.get('markerPoint', []),
                "center": center,
                "x": x,
                "y": y,
                "geometry": bld_info.get('geometry', {})
            }
            buildings_data_list.append(building_data)
        
        # 파일명에 분할 번호 및 지역명 포함
        region_suffix = "_mokdong" if 'mokdong' in args.token_file.lower() else ""
        if SPLIT_MODE and SPLIT_INDEX:
            file_suffix = f"{timestamp}_split{SPLIT_INDEX:02d}{region_suffix}"
        else:
            file_suffix = f"{timestamp}{region_suffix}"
        buildings_json_file = output_dir / f"openup_seoul_gyeonggi_buildings_{file_suffix}.json"
        with open(buildings_json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "data": buildings_data_list,
                "metadata": {
                    "timestamp": timestamp,
                    "total_buildings": len(buildings_data_list),
                    "collection_method": "hash_to_sales",
                    "cell_tokens_used": SEOUL_GYEONGGI_CELL_TOKENS,
                    "split_mode": SPLIT_MODE and SPLIT_INDEX is not None,
                    "split_index": SPLIT_INDEX if SPLIT_MODE and SPLIT_INDEX else None,
                    "split_count": SPLIT_COUNT if SPLIT_MODE else None
                }
            }, f, ensure_ascii=False, indent=2)
        
        log_and_print(f"✓ 건물 JSON 저장: {buildings_json_file}")
        
        if buildings_data_list:
            buildings_csv_file = output_dir / f"openup_seoul_gyeonggi_buildings_{file_suffix}.csv"
            FileHandler.save_csv(buildings_data_list, buildings_csv_file)
            log_and_print(f"✓ 건물 CSV 저장: {buildings_csv_file}")
        
        # 5-2. 매장 데이터 저장
        log_and_print("\n[5-2] 매장 데이터 저장")
        
        # 매장 데이터에 x, y 좌표 추가 (CSV용)
        stores_data_for_csv = []
        for store_data in sales_data_list:
            coordinates = store_data.get('coordinates', [])
            # coordinates에서 x, y 좌표 추출
            x = None
            y = None
            if isinstance(coordinates, list) and len(coordinates) >= 2:
                x = float(coordinates[0]) if coordinates[0] is not None else None
                y = float(coordinates[1]) if coordinates[1] is not None else None
            
            # x, y 컬럼 추가 (coordinates 다음에 배치)
            store_data_copy = store_data.copy()
            # coordinates 필드의 위치 찾기
            if 'coordinates' in store_data_copy:
                # coordinates 다음에 x, y 삽입
                keys = list(store_data_copy.keys())
                coord_idx = keys.index('coordinates')
                # x, y를 coordinates 다음에 삽입
                new_data = {}
                for i, key in enumerate(keys):
                    new_data[key] = store_data_copy[key]
                    if i == coord_idx:
                        new_data['x'] = x
                        new_data['y'] = y
                store_data_copy = new_data
            else:
                store_data_copy['x'] = x
                store_data_copy['y'] = y
            
            stores_data_for_csv.append(store_data_copy)
        
        stores_json_file = output_dir / f"openup_seoul_gyeonggi_stores_{file_suffix}.json"
        with open(stores_json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "data": sales_data_list,  # JSON에는 원본 데이터 유지
                "metadata": {
                    "timestamp": timestamp,
                    "total_stores": len(sales_data_list),
                    "total_buildings": len(seongsu_buildings),
                    "total_store_ids": len(all_store_ids),
                    "collection_method": "hash_to_sales",
                    "cell_tokens_used": SEOUL_GYEONGGI_CELL_TOKENS,
                    "split_mode": SPLIT_MODE and SPLIT_INDEX is not None,
                    "split_index": SPLIT_INDEX if SPLIT_MODE and SPLIT_INDEX else None,
                    "split_count": SPLIT_COUNT if SPLIT_MODE else None
                }
            }, f, ensure_ascii=False, indent=2)
        
        log_and_print(f"✓ 매장 JSON 저장: {stores_json_file}")
        
        if stores_data_for_csv:
            stores_csv_file = output_dir / f"openup_seoul_gyeonggi_stores_{file_suffix}.csv"
            FileHandler.save_csv(stores_data_for_csv, stores_csv_file)
            log_and_print(f"✓ 매장 CSV 저장: {stores_csv_file}")
        
        # 5-3. Expanded CSV 변환 (옵션)
        if GENERATE_EXPANDED_CSV:
            expanded_csv_file = output_dir / f"openup_seoul_gyeonggi_stores_{file_suffix}_expanded.csv"
            convert_stores_to_expanded_csv(sales_data_list, expanded_csv_file)
            
            # 5-4. Trend 연도별 컬럼 추가
            add_trend_columns_to_expanded_csv(expanded_csv_file, sales_data_list, expanded_csv_file)
        
        log_and_print("\n" + "=" * 80)
        log_and_print("수집 완료!")
        log_and_print(f"  건물: {len(seongsu_buildings)}개")
        log_and_print(f"  storeId: {len(all_store_ids)}개")
        log_and_print(f"  매출 데이터: {len(sales_data_list)}개")
        if GENERATE_EXPANDED_CSV:
            log_and_print(f"  Expanded CSV: 생성됨")
        log_and_print("=" * 80)
        
    except Exception as e:
        log_and_print(f"\n오류 발생: {e}")
        import traceback
        log_and_print(traceback.format_exc())
        raise
    finally:
        if 'openup_client' in locals():
            openup_client.close()
        # 모니터링 스레드 종료
        if stop_monitor:
            stop_monitor.set()
            if monitor_thread and monitor_thread.is_alive():
                monitor_thread.join(timeout=1)

if __name__ == "__main__":
    main()
