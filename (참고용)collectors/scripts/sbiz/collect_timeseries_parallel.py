"""병렬 처리용 헬퍼 함수들."""

from datetime import datetime, timedelta
from typing import Dict, List, Set
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from calendar import monthrange
import time
import json

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger

logger = get_logger(__name__)

# 전역 락 (스레드 안전성)
from threading import Lock
store_history_lock = Lock()


def _save_intermediate_result(store_history: Dict, output_dir: Path, date_str: str):
    """중간 결과 저장."""
    try:
        intermediate_file = output_dir / f"intermediate_{date_str}.json"
        with open(intermediate_file, 'w', encoding='utf-8') as f:
            json.dump(store_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"중간 저장 실패: {e}")


def _process_single_date(
    date_str: str,
    target_bizes_ids: Set[str],
    store_history: Dict[str, Dict]
) -> int:
    """단일 날짜 처리 (병렬 처리용).
    
    Args:
        date_str: 날짜 (YYYYMMDD)
        target_bizes_ids: 대상 업소 ID 집합 (None이면 모든 업소)
        store_history: 업소별 변경 이력 딕셔너리 (공유)
        
    Returns:
        처리된 업소 수
    """
    client = SBIZAPIClient()
    try:
        changed_stores = client.get_all_stores_by_date(date_str)
        
        if not changed_stores:
            return 0
        
        count = 0
        for store in changed_stores:
            bizes_id = store.get('bizesId')
            if not bizes_id:
                continue
            
            # 대상 업소 필터링 (성수동만)
            if target_bizes_ids and bizes_id not in target_bizes_ids:
                continue
            
            chg_gb = store.get('chgGb', '').strip()
            
            # 스레드 안전하게 업소별 이력 초기화 및 업데이트
            with store_history_lock:
                if bizes_id not in store_history:
                    store_history[bizes_id] = {
                        'bizesId': bizes_id,
                        'bizesNm': store.get('bizesNm', ''),
                        'openDate': None,
                        'closeDate': None,
                        'changeHistory': []
                    }
                
                # 변경 이력 추가
                change_info = {
                    'date': date_str,
                    'chgGb': chg_gb,
                    'description': {
                        'C': '신규 개업',
                        'U': '정보 수정',
                        'D': '폐업'
                    }.get(chg_gb, f'변경 ({chg_gb})')
                }
                store_history[bizes_id]['changeHistory'].append(change_info)
                
                # 개폐업일 업데이트
                if chg_gb == 'C' and not store_history[bizes_id]['openDate']:
                    store_history[bizes_id]['openDate'] = date_str
                elif chg_gb == 'D':
                    store_history[bizes_id]['closeDate'] = date_str
            
            count += 1
        
        return count
    except Exception as e:
        logger.warning(f"  {date_str} 처리 중 오류: {e}")
        return 0
    finally:
        client.close()


def _process_dates_parallel(
    all_dates: List[str],
    target_bizes_ids: Set[str],
    store_history: Dict[str, Dict],
    output_dir: Path,
    start: datetime,
    end: datetime,
    total_months: int,
    max_workers: int = 5
):
    """병렬 처리로 날짜별 데이터 수집."""
    from calendar import monthrange
    import sys
    
    # 월별로 그룹화
    month_groups = {}
    for date_str in all_dates:
        month_str = date_str[:6]  # YYYYMM
        if month_str not in month_groups:
            month_groups[month_str] = []
        month_groups[month_str].append(date_str)
    
    processed_months = 0
    total_dates_processed = 0
    total_dates = len(all_dates)
    
    # 월별로 순차 처리 (병렬은 월 내 날짜들 간에만)
    current_month_start = datetime(start.year, start.month, 1)
    end_month_start = datetime(end.year, end.month, 1)
    current_month = current_month_start
    
    while current_month <= end_month_start:
        processed_months += 1
        month_str = current_month.strftime("%Y%m")
        year = current_month.year
        month = current_month.month
        
        if month_str not in month_groups:
            # 다음 월로 이동
            if month == 12:
                current_month = datetime(year + 1, 1, 1)
            else:
                current_month = datetime(year, month + 1, 1)
            continue
        
        month_dates = month_groups[month_str]
        overall_progress = (total_dates_processed / total_dates) * 100 if total_dates > 0 else 0
        logger.info(f"[{processed_months}/{total_months}] {month_str}월 처리 중... ({len(month_dates)}일) | 전체 진행률: {overall_progress:.1f}% ({total_dates_processed:,}/{total_dates:,}일)")
        
        month_store_count = 0
        
        # 월 내 날짜들을 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_date = {
                executor.submit(_process_single_date, date_str, target_bizes_ids, store_history): date_str
                for date_str in month_dates
            }
            
            # 완료된 작업 처리
            completed = 0
            start_time = time.time()
            for future in as_completed(future_to_date):
                date_str = future_to_date[future]
                try:
                    count = future.result()
                    month_store_count += count
                    completed += 1
                    total_dates_processed += 1
                    
                    # 진행률 계산
                    month_progress = (completed / len(month_dates)) * 100 if len(month_dates) > 0 else 0
                    overall_progress = (total_dates_processed / total_dates) * 100 if total_dates > 0 else 0
                    
                    # 진행 바 생성 (20칸)
                    month_bar_length = 20
                    month_filled = int(month_progress / 100 * month_bar_length)
                    month_bar = '█' * month_filled + '░' * (month_bar_length - month_filled)
                    
                    overall_bar_length = 20
                    overall_filled = int(overall_progress / 100 * overall_bar_length)
                    overall_bar = '█' * overall_filled + '░' * (overall_bar_length - overall_filled)
                    
                    # 진행 상황 로그
                    if len(month_dates) <= 10:
                        # 날짜가 적으면 매일 로그
                        logger.info(f"  [{month_bar}] {month_str}월: {completed}/{len(month_dates)}일 ({month_progress:.1f}%) | {date_str} 완료: {count}개 업소")
                    elif completed % max(1, len(month_dates) // 10) == 0 or completed == len(month_dates):
                        # 10%마다 또는 완료 시
                        elapsed = time.time() - start_time
                        if completed > 0:
                            avg_time_per_date = elapsed / completed
                            remaining_dates = len(month_dates) - completed
                            estimated_remaining = avg_time_per_date * remaining_dates
                            logger.info(f"  [{month_bar}] {month_str}월: {completed}/{len(month_dates)}일 ({month_progress:.1f}%) | "
                                      f"[{overall_bar}] 전체: {total_dates_processed:,}/{total_dates:,}일 ({overall_progress:.1f}%) | "
                                      f"예상 남은 시간: {estimated_remaining/60:.1f}분")
                except Exception as e:
                    logger.error(f"  {date_str} 처리 실패: {e}")
                    total_dates_processed += 1
        
        # 월별 완료 로그 및 저장
        overall_progress = (total_dates_processed / total_dates) * 100 if total_dates > 0 else 0
        logger.info(f"  ✓ {month_str}월 완료: {month_store_count:,}개 업소 변경 이력 수집 | 전체 진행률: {overall_progress:.1f}% ({total_dates_processed:,}/{total_dates:,}일)")
        _save_intermediate_result(store_history, output_dir, month_str)
        
        # 다음 월로 이동
        if month == 12:
            current_month = datetime(year + 1, 1, 1)
        else:
            current_month = datetime(year, month + 1, 1)
        
        # API 호출 제한 고려 (월 간 대기)
        time.sleep(0.1)


def _process_dates_sequential(
    all_dates: List[str],
    target_bizes_ids: Set[str],
    store_history: Dict[str, Dict],
    output_dir: Path,
    start: datetime,
    end: datetime,
    total_months: int
):
    """순차 처리로 날짜별 데이터 수집."""
    from calendar import monthrange
    
    current_date = start
    current_month_str = None
    month_store_count = 0
    processed_months = 0
    total_dates = len(all_dates)
    processed_dates = 0
    
    for date_str in all_dates:
        month_str = date_str[:6]  # YYYYMM
        
        # 새로운 월 시작 시 로그 출력
        if month_str != current_month_str:
            if current_month_str is not None:
                # 이전 월 완료 로그
                overall_progress = (processed_dates / total_dates) * 100 if total_dates > 0 else 0
                logger.info(f"  ✓ {current_month_str}월 완료: {month_store_count:,}개 업소 변경 이력 수집 | 전체 진행률: {overall_progress:.1f}%")
                # 월별 중간 저장
                _save_intermediate_result(store_history, output_dir, current_month_str)
            
            processed_months += 1
            current_month_str = month_str
            month_store_count = 0
            overall_progress = (processed_dates / total_dates) * 100 if total_dates > 0 else 0
            logger.info(f"[{processed_months}/{total_months}] {month_str}월 처리 중... | 전체 진행률: {overall_progress:.1f}% ({processed_dates:,}/{total_dates:,}일)")
        
        # 단일 날짜 처리
        count = _process_single_date(date_str, target_bizes_ids, store_history)
        month_store_count += count
        processed_dates += 1
        
        # 진행률 표시 (10%마다 또는 매일)
        overall_progress = (processed_dates / total_dates) * 100 if total_dates > 0 else 0
        if processed_dates % max(1, total_dates // 20) == 0 or processed_dates == total_dates:
            # 진행 바 생성
            bar_length = 30
            filled = int(overall_progress / 100 * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            logger.info(f"  [{bar}] 전체 진행률: {overall_progress:.1f}% ({processed_dates:,}/{total_dates:,}일) | {date_str} 완료: {count}개 업소")
        
        # API 호출 제한 고려 (초당 30 tps)
        time.sleep(0.05)  # 약 20 tps로 제한
    
    # 마지막 월 완료 로그 및 저장
    if current_month_str:
        overall_progress = (processed_dates / total_dates) * 100 if total_dates > 0 else 0
        logger.info(f"  ✓ {current_month_str}월 완료: {month_store_count:,}개 업소 변경 이력 수집 | 전체 진행률: {overall_progress:.1f}% ({processed_dates:,}/{total_dates:,}일)")
        _save_intermediate_result(store_history, output_dir, current_month_str)

