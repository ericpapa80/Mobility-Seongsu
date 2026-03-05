"""OpenUp 웹사이트를 자동으로 탐색하여 cell-tokens를 수집하는 스크립트.

이 스크립트는 Playwright를 사용하여 OpenUp 웹사이트를 자동으로 탐색하고,
Network 요청을 가로채서 `/v2/pro/gp` 요청의 `hashKeys` 필드에서 cell-tokens를 수집합니다.

사용 방법:
    python collectors/scripts/openup/auto_collect_cell_tokens.py
    python collectors/scripts/openup/auto_collect_cell_tokens.py --region seoul
    python collectors/scripts/openup/auto_collect_cell_tokens.py --output 260115_token
"""

import sys
import asyncio
import json
import re
from pathlib import Path
from typing import Set, Dict, List, Optional, Tuple
from datetime import datetime
import argparse
from collections import defaultdict

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright가 설치되지 않았습니다. 다음 명령어로 설치하세요:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger

logger = get_logger(__name__)

# OpenUp 웹사이트 URL
OPENUP_URL = "https://pro.openub.com"

# 수집된 cell-tokens 저장
collected_tokens: Set[str] = set()
collected_access_tokens: Set[str] = set()
collected_bboxes: List[Dict] = []  # 수집된 bbox 정보
request_lock = asyncio.Lock()
last_token_collection_time: float = 0.0  # 마지막 token 수집 시간


async def setup_network_handlers(context, page: Page):
    """Network 요청/응답 핸들러를 Context와 Page에 등록 (capture_gp_requests.py 방식).
    
    Args:
        context: BrowserContext 객체
        page: Page 객체
    """
    
    async def response_handler(response):
        """응답 핸들러 - gp 요청과 coord 요청 처리."""
        url = response.url
        
        # /v2/pro/gp 요청 처리
        if '/v2/pro/gp' in url:
            try:
                request = response.request
                
                # Request Payload에서 hashKeys 추출
                post_data = request.post_data
                if post_data:
                    payload = json.loads(post_data)
                    if 'hashKeys' in payload:
                        hash_keys = payload['hashKeys']
                        if isinstance(hash_keys, list):
                            async with request_lock:
                                for key in hash_keys:
                                    if isinstance(key, str) and len(key) == 8 and all(c in '0123456789abcdef' for c in key.lower()):
                                        if key not in collected_tokens:
                                            collected_tokens.add(key)
                                            global last_token_collection_time
                                            last_token_collection_time = asyncio.get_event_loop().time()
                                            logger.info(f"✓ Cell-token 수집: {key}")
                
                # Response Body에서도 hashKeys 추출 (response body의 키가 hashKeys일 수 있음)
                try:
                    response_body = await response.json()
                    if isinstance(response_body, dict):
                        import re
                        hex_pattern = re.compile(r'^[0-9a-f]{8}$', re.IGNORECASE)
                        response_hash_keys = [key for key in response_body.keys() if hex_pattern.match(key)]
                        async with request_lock:
                            for key in response_hash_keys:
                                if key not in collected_tokens:
                                    collected_tokens.add(key)
                                    logger.info(f"✓ Cell-token 수집 (응답에서): {key}")
                except:
                    pass
            except Exception as e:
                logger.debug(f"gp 요청 처리 중 오류: {e}")
        
        # /v2/pro/coord 요청에서 bbox 추출
        if '/v2/pro/coord' in url:
            try:
                request = response.request
                post_data = request.post_data
                if post_data:
                    payload = json.loads(post_data)
                    if 'bbox' in payload:
                        bbox = payload['bbox']
                        async with request_lock:
                            collected_bboxes.append(bbox)
                            logger.info(f"✓ bbox 수집: NE({bbox.get('ne', {}).get('lng')}, {bbox.get('ne', {}).get('lat')}), SW({bbox.get('sw', {}).get('lng')}, {bbox.get('sw', {}).get('lat')})")
            except Exception as e:
                logger.debug(f"coord 요청 처리 중 오류: {e}")
    
    async def request_handler(request):
        """요청 핸들러 - access-token 수집."""
        # access-token 수집 (Headers에서)
        access_token = request.headers.get('access-token')
        if access_token:
            async with request_lock:
                if access_token not in collected_access_tokens:
                    collected_access_tokens.add(access_token)
                    logger.debug(f"✓ Access-token 수집: {access_token[:20]}...")
    
    # Context에 핸들러 등록 (페이지 생성 전에 등록 - 중요!)
    context.on("request", request_handler)
    context.on("response", response_handler)
    logger.debug("✓ Context 핸들러 등록 완료 (페이지 생성 전)")
    
    # Page에도 핸들러 등록 (중복 등록해도 안전)
    page.on("request", request_handler)
    page.on("response", response_handler)
    logger.debug("✓ Page 핸들러 등록 완료")


async def get_current_map_center(page: Page) -> Optional[Tuple[float, float]]:
    """현재 지도 중심 좌표를 가져옴.
    
    Returns:
        (경도, 위도) 튜플 또는 None
    """
    try:
        # 다양한 지도 라이브러리에서 중심 좌표 가져오기
        get_center_scripts = [
            # OpenLayers
            """
            if (window.map && window.map.getView) {
                var center = window.map.getView().getCenter();
                if (center && ol.proj) {
                    var lonlat = ol.proj.toLonLat(center);
                    return {lng: lonlat[0], lat: lonlat[1]};
                }
            }
            return null;
            """,
            # Leaflet
            """
            if (window.map && window.map.getCenter) {
                var center = window.map.getCenter();
                return {lng: center.lng, lat: center.lat};
            }
            return null;
            """,
            # 일반적인 지도 객체
            """
            if (window.map && window.map.getCenter) {
                var center = window.map.getCenter();
                if (Array.isArray(center)) {
                    return {lng: center[0], lat: center[1]};
                } else if (center.lng && center.lat) {
                    return {lng: center.lng, lat: center.lat};
                }
            }
            return null;
            """
        ]
        
        for script in get_center_scripts:
            try:
                result = await page.evaluate(script)
                if result and 'lng' in result and 'lat' in result:
                    return (result['lng'], result['lat'])
            except:
                continue
        
        return None
    except:
        return None


async def find_map_object(page: Page) -> Optional[Dict]:
    """페이지에서 지도 객체를 찾아 반환.
    
    Returns:
        지도 객체 정보 딕셔너리 또는 None
    """
    try:
        find_map_script = """
        (function() {
            // 모든 가능한 지도 객체 찾기
            var mapObjects = {};
            
            // window 객체에서 찾기
            for (var key in window) {
                try {
                    var obj = window[key];
                    if (obj && typeof obj === 'object') {
                        // OpenLayers 지도
                        if (obj.getView && typeof obj.getView === 'function') {
                            mapObjects['window.' + key] = 'OpenLayers';
                        }
                        // Leaflet 지도
                        if (obj.setView && typeof obj.setView === 'function') {
                            mapObjects['window.' + key] = 'Leaflet';
                        }
                        // 일반 지도
                        if (obj.setCenter || obj.panTo || obj.fitBounds) {
                            mapObjects['window.' + key] = 'Generic';
                        }
                    }
                } catch(e) {}
            }
            
            // React/Vue 등 프레임워크에서 찾기
            if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
                mapObjects['react'] = 'React';
            }
            if (window.__VUE__) {
                mapObjects['vue'] = 'Vue';
            }
            
            return {
                found: Object.keys(mapObjects).length > 0,
                objects: mapObjects,
                olAvailable: typeof ol !== 'undefined',
                leafletAvailable: typeof L !== 'undefined'
            };
        })();
        """
        
        result = await page.evaluate(find_map_script)
        return result
    except:
        return None


async def simulate_mouse_drag_to_location(page: Page, target_lng: float, target_lat: float, steps: int = 20):
    """마우스 드래그를 시뮬레이션하여 지도를 특정 위치로 이동 (개선된 버전).
    
    Args:
        page: Playwright Page 객체
        target_lng: 목표 경도
        target_lat: 목표 위도
        steps: 드래그 단계 수 (더 많을수록 부드러움)
    """
    logger.info(f"🖱️ 마우스 드래그로 지도 이동: ({target_lng}, {target_lat})")
    
    try:
        # 현재 지도 중심 좌표 가져오기
        current_center = await get_current_map_center(page)
        if not current_center:
            logger.warning("  ⚠️ 현재 지도 중심을 확인할 수 없습니다.")
            return False
        
        current_lng, current_lat = current_center
        logger.info(f"  현재 중심: ({current_lng:.4f}, {current_lat:.4f})")
        
        # 지도 컨테이너 찾기
        map_selectors = ['#map', '.map', '[class*="map"]', 'canvas', '[id*="map"]']
        map_element = None
        
        for selector in map_selectors:
            try:
                map_element = await page.wait_for_selector(selector, timeout=2000)
                if map_element:
                    break
            except:
                continue
        
        if not map_element:
            logger.warning("  ⚠️ 지도 컨테이너를 찾을 수 없습니다.")
            return False
        
        box = await map_element.bounding_box()
        if not box:
            logger.warning("  ⚠️ 지도 크기를 확인할 수 없습니다.")
            return False
        
        center_x = box['width'] / 2
        center_y = box['height'] / 2
        
        # 좌표 차이 계산
        lng_diff = target_lng - current_lng
        lat_diff = target_lat - current_lat
        
        # 픽셀 변환 (대략적인 계산)
        zoom_level = 15  # 기본값
        try:
            zoom_script = """
            (function() {
                if (window.map && window.map.getView && window.map.getView().getZoom) {
                    return window.map.getView().getZoom();
                }
                if (window.map && window.map.getZoom) {
                    return window.map.getZoom();
                }
                return 15;
            })();
            """
            zoom_level = await page.evaluate(zoom_script)
        except:
            pass
        
        # 줌 레벨에 따른 픽셀 변환 (대략적)
        pixels_per_degree_lng = 200 * (2 ** (zoom_level - 15))
        pixels_per_degree_lat = 200 * (2 ** (zoom_level - 15))
        
        # 드래그 거리 계산 (위도는 반대 방향)
        drag_x = lng_diff * pixels_per_degree_lng
        drag_y = -lat_diff * pixels_per_degree_lat  # 위도는 반대
        
        logger.info(f"  드래그 거리: X={drag_x:.1f}px, Y={drag_y:.1f}px (줌 레벨: {zoom_level})")
        
        # 방법 1: JavaScript로 직접 마우스 이벤트 발생 (더 확실함)
        try:
            event_script = f"""
            (function() {{
                var mapElement = document.querySelector('#map, .map, [class*="map"], canvas, [id*="map"]');
                if (!mapElement) return false;
                
                var rect = mapElement.getBoundingClientRect();
                var centerX = rect.left + rect.width / 2;
                var centerY = rect.top + rect.height / 2;
                
                // mousedown 이벤트
                var mouseDown = new MouseEvent('mousedown', {{
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: centerX,
                    clientY: centerY,
                    button: 0,
                    buttons: 1
                }});
                mapElement.dispatchEvent(mouseDown);
                
                // mousemove 이벤트들 (단계별)
                var steps = {steps};
                var stepX = {drag_x} / steps;
                var stepY = {drag_y} / steps;
                
                for (var i = 1; i <= steps; i++) {{
                    var moveX = centerX + stepX * i;
                    var moveY = centerY + stepY * i;
                    var mouseMove = new MouseEvent('mousemove', {{
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: moveX,
                        clientY: moveY,
                        button: 0,
                        buttons: 1
                    }});
                    mapElement.dispatchEvent(mouseMove);
                    document.dispatchEvent(mouseMove);
                }}
                
                // mouseup 이벤트
                var finalX = centerX + {drag_x};
                var finalY = centerY + {drag_y};
                var mouseUp = new MouseEvent('mouseup', {{
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: finalX,
                    clientY: finalY,
                    button: 0,
                    buttons: 0
                }});
                mapElement.dispatchEvent(mouseUp);
                document.dispatchEvent(mouseUp);
                
                return true;
            }})();
            """
            
            result = await page.evaluate(event_script)
            if result:
                await asyncio.sleep(2)
                logger.info("  ✓ JavaScript 이벤트로 드래그 시도")
        except Exception as e:
            logger.debug(f"  JavaScript 이벤트 실패: {e}")
        
        # 방법 2: Playwright 마우스 API 사용 (절대 좌표 사용)
        try:
            box_abs = await map_element.bounding_box()
            if box_abs:
                center_x_abs = box_abs['x'] + box_abs['width'] / 2
                center_y_abs = box_abs['y'] + box_abs['height'] / 2
                
                await page.mouse.move(center_x_abs, center_y_abs)
                await asyncio.sleep(0.3)
                
                await page.mouse.down(button='left')
                await asyncio.sleep(0.1)
                
                step_x = drag_x / steps
                step_y = drag_y / steps
                
                for i in range(1, steps + 1):
                    new_x = center_x_abs + step_x * i
                    new_y = center_y_abs + step_y * i
                    await page.mouse.move(new_x, new_y)
                    await asyncio.sleep(0.02)
                
                await page.mouse.up(button='left')
                await asyncio.sleep(1.5)
                
                logger.info("  ✓ Playwright 마우스 API로 드래그 완료")
        except Exception as e:
            logger.debug(f"  Playwright 마우스 드래그 실패: {e}")
        
        # 이동 확인
        await asyncio.sleep(1)
        new_center = await get_current_map_center(page)
        if new_center:
            new_lng, new_lat = new_center
            lng_diff_after = abs(new_lng - target_lng)
            lat_diff_after = abs(new_lat - target_lat)
            
            logger.info(f"  이동 후 중심: ({new_lng:.4f}, {new_lat:.4f})")
            logger.info(f"  목표와의 차이: 경도 {lng_diff_after:.4f}, 위도 {lat_diff_after:.4f}")
            
            if lng_diff_after < 0.01 and lat_diff_after < 0.01:
                logger.info("  ✅ 마우스 드래그로 이동 성공!")
                return True
            else:
                logger.info("  ⚠️ 이동이 완전하지 않습니다. 추가 조정 필요.")
                return False
        else:
            logger.warning("  ⚠️ 이동 후 중심 좌표를 확인할 수 없습니다.")
            return False
            
    except Exception as e:
        logger.warning(f"  마우스 드래그 실패: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


async def use_map_controls(page: Page, direction: str = "center"):
    """지도 컨트롤 버튼을 사용하여 지도 이동.
    
    Args:
        page: Playwright Page 객체
        direction: 이동 방향 ("up", "down", "left", "right", "center", "zoom_in", "zoom_out")
    """
    try:
        # 지도 컨트롤 버튼 선택자들
        control_selectors = {
            "up": ['button[title*="위"], button[title*="Up"], .map-control-up, [class*="north"]'],
            "down": ['button[title*="아래"], button[title*="Down"], .map-control-down, [class*="south"]'],
            "left": ['button[title*="왼쪽"], button[title*="Left"], .map-control-left, [class*="west"]'],
            "right": ['button[title*="오른쪽"], button[title*="Right"], .map-control-right, [class*="east"]'],
            "zoom_in": ['button[title*="확대"], button[title*="Zoom in"], .map-zoom-in, [class*="zoom-in"]'],
            "zoom_out": ['button[title*="축소"], button[title*="Zoom out"], .map-zoom-out, [class*="zoom-out"]']
        }
        
        if direction in control_selectors:
            for selector in control_selectors[direction]:
                try:
                    button = await page.wait_for_selector(selector, timeout=1000)
                    if button:
                        await button.click()
                        await asyncio.sleep(0.5)
                        logger.info(f"  ✓ {direction} 컨트롤 버튼 클릭")
                        return True
                except:
                    continue
        
        return False
    except Exception as e:
        logger.debug(f"  지도 컨트롤 사용 실패: {e}")
        return False


async def search_address_and_move(page: Page, address: str):
    """주소 검색을 통해 지도 이동.
    
    Args:
        page: Playwright Page 객체
        address: 검색할 주소 (예: "서울특별시 성동구 성수동")
    """
    logger.info(f"🔍 주소 검색으로 지도 이동: {address}")
    
    try:
        # 검색창 찾기
        search_selectors = [
            'input[type="search"]',
            'input[placeholder*="검색"]',
            'input[placeholder*="지역"]',
            'input[placeholder*="주소"]',
            '.search-input',
            '#search',
            'input[class*="search"]',
            '[role="searchbox"]'
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = await page.wait_for_selector(selector, timeout=2000)
                if search_input:
                    break
            except:
                continue
        
        if not search_input:
            logger.warning("  ⚠️ 검색창을 찾을 수 없습니다.")
            return False
        
        # 검색어 입력
        await search_input.click()
        await asyncio.sleep(0.5)
        await search_input.fill(address)
        await asyncio.sleep(1)
        
        # Enter 키 또는 검색 버튼 클릭
        await page.keyboard.press('Enter')
        await asyncio.sleep(3)  # 검색 결과 대기
        
        # 검색 결과 클릭 (있는 경우)
        result_selectors = [
            '.search-result',
            '[class*="result"]',
            '[class*="suggestion"]',
            'li[role="option"]'
        ]
        
        for selector in result_selectors:
            try:
                result = await page.wait_for_selector(selector, timeout=2000)
                if result:
                    await result.click()
                    await asyncio.sleep(2)
                    logger.info("  ✓ 검색 결과 클릭")
                    break
            except:
                continue
        
        logger.info("  ✓ 주소 검색 완료")
        return True
        
    except Exception as e:
        logger.warning(f"  주소 검색 실패: {e}")
        return False


async def simulate_mouse_drag_to_location(page: Page, target_lng: float, target_lat: float, steps: int = 30):
    """마우스 드래그를 시뮬레이션하여 지도를 특정 위치로 이동.
    
    Args:
        page: Playwright Page 객체
        target_lng: 목표 경도
        target_lat: 목표 위도
        steps: 드래그 단계 수 (더 많을수록 부드러움)
    """
    logger.info(f"🖱️ 마우스 드래그로 지도 이동: ({target_lng}, {target_lat})")
    
    try:
        # 현재 지도 중심 좌표 가져오기
        current_center = await get_current_map_center(page)
        if not current_center:
            logger.warning("  ⚠️ 현재 지도 중심을 확인할 수 없습니다.")
            return False
        
        current_lng, current_lat = current_center
        logger.info(f"  현재 중심: ({current_lng:.4f}, {current_lat:.4f})")
        
        # 지도 컨테이너 찾기
        map_selectors = ['#map', '.map', '[class*="map"]', 'canvas', '[id*="map"]']
        map_element = None
        
        for selector in map_selectors:
            try:
                map_element = await page.wait_for_selector(selector, timeout=2000)
                if map_element:
                    break
            except:
                continue
        
        if not map_element:
            logger.warning("  ⚠️ 지도 컨테이너를 찾을 수 없습니다.")
            return False
        
        box = await map_element.bounding_box()
        if not box:
            logger.warning("  ⚠️ 지도 크기를 확인할 수 없습니다.")
            return False
        
        center_x = box['width'] / 2
        center_y = box['height'] / 2
        
        # 좌표 차이 계산
        lng_diff = target_lng - current_lng
        lat_diff = target_lat - current_lat
        
        # 픽셀 변환 (대략적인 계산)
        zoom_level = 15  # 기본값
        try:
            zoom_script = """
            (function() {
                if (window.map && window.map.getView && window.map.getView().getZoom) {
                    return window.map.getView().getZoom();
                }
                if (window.map && window.map.getZoom) {
                    return window.map.getZoom();
                }
                return 15;
            })();
            """
            zoom_level = await page.evaluate(zoom_script)
        except:
            pass
        
        # 줌 레벨에 따른 픽셀 변환 (대략적)
        pixels_per_degree_lng = 200 * (2 ** (zoom_level - 15))
        pixels_per_degree_lat = 200 * (2 ** (zoom_level - 15))
        
        # 드래그 거리 계산 (위도는 반대 방향)
        drag_x = lng_diff * pixels_per_degree_lng
        drag_y = -lat_diff * pixels_per_degree_lat  # 위도는 반대
        
        logger.info(f"  드래그 거리: X={drag_x:.1f}px, Y={drag_y:.1f}px (줌 레벨: {zoom_level})")
        
        # 지도 중앙으로 마우스 이동
        await map_element.hover(position={'x': center_x, 'y': center_y})
        await asyncio.sleep(0.5)
        
        # 마우스 다운
        await page.mouse.move(center_x, center_y)
        await page.mouse.down()
        await asyncio.sleep(0.1)
        
        # 단계별로 드래그 (부드러운 이동)
        step_x = drag_x / steps
        step_y = drag_y / steps
        
        for i in range(1, steps + 1):
            new_x = center_x + step_x * i
            new_y = center_y + step_y * i
            await page.mouse.move(new_x, new_y)
            await asyncio.sleep(0.05)  # 각 단계마다 짧은 대기
        
        # 마우스 업
        await page.mouse.up()
        await asyncio.sleep(1)  # 지도 이동 완료 대기
        
        # 이동 확인
        new_center = await get_current_map_center(page)
        if new_center:
            new_lng, new_lat = new_center
            lng_diff_after = abs(new_lng - target_lng)
            lat_diff_after = abs(new_lat - target_lat)
            
            logger.info(f"  이동 후 중심: ({new_lng:.4f}, {new_lat:.4f})")
            logger.info(f"  목표와의 차이: 경도 {lng_diff_after:.4f}, 위도 {lat_diff_after:.4f}")
            
            if lng_diff_after < 0.01 and lat_diff_after < 0.01:
                logger.info("  ✅ 마우스 드래그로 이동 성공!")
                return True
            else:
                logger.info("  ⚠️ 이동이 완전하지 않습니다. 추가 조정 필요.")
                return False
        else:
            logger.warning("  ⚠️ 이동 후 중심 좌표를 확인할 수 없습니다.")
            return False
            
    except Exception as e:
        logger.warning(f"  마우스 드래그 실패: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


async def search_address_and_move(page: Page, address: str):
    """주소 검색을 통해 지도 이동.
    
    Args:
        page: Playwright Page 객체
        address: 검색할 주소 (예: "서울특별시 성동구 성수동")
    """
    logger.info(f"🔍 주소 검색으로 지도 이동: {address}")
    
    try:
        # 검색창 찾기
        search_selectors = [
            'input[type="search"]',
            'input[placeholder*="검색"]',
            'input[placeholder*="지역"]',
            'input[placeholder*="주소"]',
            '.search-input',
            '#search',
            'input[class*="search"]',
            '[role="searchbox"]'
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = await page.wait_for_selector(selector, timeout=2000)
                if search_input:
                    break
            except:
                continue
        
        if not search_input:
            logger.warning("  ⚠️ 검색창을 찾을 수 없습니다.")
            return False
        
        # 검색어 입력
        await search_input.click()
        await asyncio.sleep(0.5)
        await search_input.fill(address)
        await asyncio.sleep(1)
        
        # Enter 키 또는 검색 버튼 클릭
        await page.keyboard.press('Enter')
        await asyncio.sleep(3)  # 검색 결과 대기
        
        # 검색 결과 클릭 (있는 경우)
        result_selectors = [
            '.search-result',
            '[class*="result"]',
            '[class*="suggestion"]',
            'li[role="option"]'
        ]
        
        for selector in result_selectors:
            try:
                result = await page.wait_for_selector(selector, timeout=2000)
                if result:
                    await result.click()
                    await asyncio.sleep(2)
                    logger.info("  ✓ 검색 결과 클릭")
                    break
            except:
                continue
        
        logger.info("  ✓ 주소 검색 완료")
        return True
        
    except Exception as e:
        logger.warning(f"  주소 검색 실패: {e}")
        return False


async def use_map_controls(page: Page, direction: str = "center"):
    """지도 컨트롤 버튼을 사용하여 지도 이동.
    
    Args:
        page: Playwright Page 객체
        direction: 이동 방향 ("up", "down", "left", "right", "center", "zoom_in", "zoom_out")
    """
    try:
        # 지도 컨트롤 버튼 선택자들
        control_selectors = {
            "up": ['button[title*="위"], button[title*="Up"], .map-control-up, [class*="north"]'],
            "down": ['button[title*="아래"], button[title*="Down"], .map-control-down, [class*="south"]'],
            "left": ['button[title*="왼쪽"], button[title*="Left"], .map-control-left, [class*="west"]'],
            "right": ['button[title*="오른쪽"], button[title*="Right"], .map-control-right, [class*="east"]'],
            "zoom_in": ['button[title*="확대"], button[title*="Zoom in"], .map-zoom-in, [class*="zoom-in"]'],
            "zoom_out": ['button[title*="축소"], button[title*="Zoom out"], .map-zoom-out, [class*="zoom-out"]']
        }
        
        if direction in control_selectors:
            for selector in control_selectors[direction]:
                try:
                    button = await page.wait_for_selector(selector, timeout=1000)
                    if button:
                        await button.click()
                        await asyncio.sleep(0.5)
                        logger.info(f"  ✓ {direction} 컨트롤 버튼 클릭")
                        return True
                except:
                    continue
        
        return False
    except Exception as e:
        logger.debug(f"  지도 컨트롤 사용 실패: {e}")
        return False


async def move_map_with_bbox(page: Page, ne_lng: float, ne_lat: float, sw_lng: float, sw_lat: float, region_name: str = None):
    """bbox를 사용하여 지도를 특정 영역으로 이동.
    
    Args:
        page: Playwright Page 객체
        ne_lng: 북동쪽 경도
        ne_lat: 북동쪽 위도
        sw_lng: 남서쪽 경도
        sw_lat: 남서쪽 위도
    """
    logger.info(f"🗺️ bbox로 지도 이동: NE({ne_lng}, {ne_lat}), SW({sw_lng}, {sw_lat})")
    
    # 지도 객체 찾기
    map_info = await find_map_object(page)
    if map_info:
        logger.info(f"  발견된 지도 정보: {map_info}")
    
    try:
        # 방법 1: Network 요청을 직접 생성하여 지도 업데이트 트리거
        # OpenUp 웹사이트는 coord API 호출 시 지도가 자동으로 업데이트될 수 있음
        try:
            # access-token 가져오기
            access_token_script = """
            (function() {
                // localStorage, sessionStorage, cookies에서 찾기
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    if (key && key.toLowerCase().includes('token')) {
                        return localStorage.getItem(key);
                    }
                }
                return null;
            })();
            """
            
            stored_token = await page.evaluate(access_token_script)
            
            # coord API 직접 호출
            coord_script = f"""
            (async function() {{
                try {{
                    // access-token 찾기
                    var token = null;
                    // localStorage에서 찾기
                    for (var i = 0; i < localStorage.length; i++) {{
                        var key = localStorage.key(i);
                        if (key && key.toLowerCase().includes('token')) {{
                            token = localStorage.getItem(key);
                            break;
                        }}
                    }}
                    // sessionStorage에서 찾기
                    if (!token) {{
                        for (var i = 0; i < sessionStorage.length; i++) {{
                            var key = sessionStorage.key(i);
                            if (key && key.toLowerCase().includes('token')) {{
                                token = sessionStorage.getItem(key);
                                break;
                            }}
                        }}
                    }}
                    
                    var headers = {{
                        'Content-Type': 'application/json',
                        'accept': '*/*',
                        'origin': 'https://pro.openub.com',
                        'referer': 'https://pro.openub.com/'
                    }};
                    
                    if (token) {{
                        headers['access-token'] = token;
                    }}
                    
                    var response = await fetch('https://api.openub.com/v2/pro/coord', {{
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify({{
                            bbox: {{
                                ne: {{lng: "{ne_lng}", lat: "{ne_lat}"}},
                                sw: {{lng: "{sw_lng}", lat: "{sw_lat}"}}
                            }}
                        }})
                    }});
                    
                    var result = await response.json();
                    console.log('Coord API result:', result);
                    
                    // 지도 업데이트 트리거를 위해 이벤트 발생
                    window.dispatchEvent(new CustomEvent('mapbboxchange', {{
                        detail: {{
                            bbox: {{
                                ne: {{lng: {ne_lng}, lat: {ne_lat}}},
                                sw: {{lng: {sw_lng}, lat: {sw_lat}}}
                            }},
                            result: result
                        }}
                    }}));
                    
                    return result;
                }} catch(e) {{
                    console.error('Coord API error:', e);
                    return {{error: e.message}};
                }}
            }})();
            """
            
            result = await page.evaluate(coord_script)
            await asyncio.sleep(2)
            logger.info(f"  ✓ coord API 호출: {result}")
        except Exception as e:
            logger.debug(f"  coord API 호출 실패: {e}")
        
        # 방법 2: JavaScript로 지도 객체 직접 조작 (강화)
        bbox_scripts = [
            # OpenLayers - 모든 가능한 방법
            f"""
            (function() {{
                if (typeof ol === 'undefined') return false;
                
                // 모든 가능한 지도 객체 찾기
                var mapObjects = [];
                for (var key in window) {{
                    try {{
                        var obj = window[key];
                        if (obj && obj.getView && typeof obj.getView === 'function') {{
                            mapObjects.push(obj);
                        }}
                    }} catch(e) {{
                    }}
                }}
                
                // document에서도 찾기
                var mapElements = document.querySelectorAll('[id*="map"], [class*="map"]');
                for (var i = 0; i < mapElements.length; i++) {{
                    if (mapElements[i].map) {{
                        mapObjects.push(mapElements[i].map);
                    }}
                }}
                
                // 각 지도 객체에 bbox 적용
                for (var i = 0; i < mapObjects.length; i++) {{
                    try {{
                        var view = mapObjects[i].getView();
                        if (view) {{
                            var extent = ol.proj.transformExtent(
                                [{sw_lng}, {sw_lat}, {ne_lng}, {ne_lat}],
                                'EPSG:4326',
                                view.getProjection()
                            );
                            view.fit(extent, {{duration: 500}});
                            return true;
                        }}
                    }} catch(e) {{
                    }}
                }}
                
                return false;
            }})();
            """,
            # Leaflet
            f"""
            (function() {{
                if (typeof L === 'undefined') return false;
                
                var mapObjects = [];
                for (var key in window) {{
                    try {{
                        var obj = window[key];
                        if (obj && obj.setView && typeof obj.setView === 'function') {{
                            mapObjects.push(obj);
                        }}
                    }} catch(e) {{
                    }}
                }}
                
                for (var i = 0; i < mapObjects.length; i++) {{
                    try {{
                        mapObjects[i].fitBounds([[{sw_lat}, {sw_lng}], [{ne_lat}, {ne_lng}]]);
                        return true;
                    }} catch(e) {{
                    }}
                }}
                
                return false;
            }})();
            """,
            # 일반적인 지도 API
            f"""
            (function() {{
                var mapObjects = [];
                for (var key in window) {{
                    try {{
                        var obj = window[key];
                        if (obj && (obj.fitBounds || obj.setBounds || obj.setCenter)) {{
                            mapObjects.push({{obj: obj, name: key}});
                        }}
                    }} catch(e) {{
                    }}
                }}
                
                for (var i = 0; i < mapObjects.length; i++) {{
                    try {{
                        var map = mapObjects[i].obj;
                        if (map.fitBounds) {{
                            map.fitBounds({{
                                ne: {{lng: {ne_lng}, lat: {ne_lat}}},
                                sw: {{lng: {sw_lng}, lat: {sw_lat}}}
                            }});
                            return true;
                        }}
                        if (map.setBounds) {{
                            map.setBounds({{
                                ne: {{lng: {ne_lng}, lat: {ne_lat}}},
                                sw: {{lng: {sw_lng}, lat: {sw_lat}}}
                            }});
                            return true;
                        }}
                    }} catch(e) {{
                    }}
                }}
                
                return false;
            }})();
            """
        ]
        
        for script in bbox_scripts:
            try:
                result = await page.evaluate(script)
                if result:
                    await asyncio.sleep(3)
                    logger.info("  ✓ JavaScript로 bbox 설정 성공")
                    break
            except Exception as e:
                logger.debug(f"  bbox 스크립트 실행 실패: {e}")
                continue
        
        # 방법 3: 마우스 드래그 시뮬레이션 (개선된 버전)
        try:
            center_lng = (ne_lng + sw_lng) / 2
            center_lat = (ne_lat + sw_lat) / 2
            
            # 현재 중심 좌표 가져오기
            current_center = await get_current_map_center(page)
            if current_center:
                current_lng, current_lat = current_center
                
                # 목표 좌표와의 차이 계산
                lng_diff = center_lng - current_lng
                lat_diff = center_lat - current_lat
                
                if abs(lng_diff) > 0.001 or abs(lat_diff) > 0.001:  # 100m 이상 차이
                    success = await simulate_mouse_drag_to_location(page, center_lng, center_lat, steps=30)
                    if success:
                        logger.info("  ✓ 마우스 드래그로 이동 성공")
                    else:
                        logger.info("  ⚠️ 마우스 드래그로 이동 시도 (부분 성공)")
        except Exception as e:
            logger.debug(f"  마우스 드래그 실패: {e}")
        
        # 방법 4: 주소 검색으로 이동 (지역명만 사용)
        try:
            # 좌표 형식은 사용하지 않고, 지역명만 사용
            if region_name:
                await search_address_and_move(page, region_name)
            else:
                # region_name이 없으면 bbox 중심 좌표로 지역 추정 시도
                # 또는 기본값 사용
                await search_address_and_move(page, "성수동")
        except Exception as e:
            logger.debug(f"  주소 검색 실패: {e}")
        
        # 방법 5: 지도 컨트롤 버튼 사용
        try:
            center_lng = (ne_lng + sw_lng) / 2
            center_lat = (ne_lat + sw_lat) / 2
            current_center = await get_current_map_center(page)
            
            if current_center:
                current_lng, current_lat = current_center
                lng_diff = center_lng - current_lng
                lat_diff = center_lat - current_lat
                
                # 방향 결정 및 컨트롤 버튼 클릭
                if abs(lng_diff) > 0.01 or abs(lat_diff) > 0.01:
                    # 여러 번 클릭하여 이동
                    if lng_diff > 0:
                        for _ in range(min(int(abs(lng_diff) * 10), 20)):  # 최대 20번
                            await use_map_controls(page, "right")
                    else:
                        for _ in range(min(int(abs(lng_diff) * 10), 20)):
                            await use_map_controls(page, "left")
                    
                    if lat_diff > 0:
                        for _ in range(min(int(abs(lat_diff) * 10), 20)):
                            await use_map_controls(page, "up")
                    else:
                        for _ in range(min(int(abs(lat_diff) * 10), 20)):
                            await use_map_controls(page, "down")
        except Exception as e:
            logger.debug(f"  지도 컨트롤 사용 실패: {e}")
        
        await asyncio.sleep(2)
        
        # 이동 확인
        new_center = await get_current_map_center(page)
        if new_center:
            center_lng = (ne_lng + sw_lng) / 2
            center_lat = (ne_lat + sw_lat) / 2
            new_lng, new_lat = new_center
            lng_diff = abs(new_lng - center_lng)
            lat_diff = abs(new_lat - center_lat)
            
            if lng_diff < 0.01 and lat_diff < 0.01:
                logger.info(f"  ✅ 지도 이동 성공! 현재 중심: ({new_lng:.4f}, {new_lat:.4f})")
                return True
            else:
                logger.warning(f"  ⚠️ 지도 이동 미완료. 현재 중심: ({new_lng:.4f}, {new_lat:.4f})")
        
        return False
        
    except Exception as e:
        logger.warning(f"  bbox 이동 중 오류: {e}")
        return False


def calculate_bbox_from_center(lng: float, lat: float, radius_km: float = 2.0) -> Tuple[float, float, float, float]:
    """중심 좌표로부터 bbox 계산.
    
    Args:
        lng: 중심 경도
        lat: 중심 위도
        radius_km: 반경 (km, 기본값: 2km)
    
    Returns:
        (ne_lng, ne_lat, sw_lng, sw_lat) 튜플
    """
    # 1도 ≈ 111km
    lng_offset = radius_km / 111.0
    lat_offset = radius_km / 111.0
    
    ne_lng = lng + lng_offset
    ne_lat = lat + lat_offset
    sw_lng = lng - lng_offset
    sw_lat = lat - lat_offset
    
    return (ne_lng, ne_lat, sw_lng, sw_lat)


def generate_seoul_grid(grid_size_km: float = 2.0) -> List[Tuple[float, float, float, float]]:
    """서울시 전체를 격자로 나누어 bbox 리스트 생성.
    
    Args:
        grid_size_km: 격자 크기 (km, 기본값: 2.0)
    
    Returns:
        bbox 리스트 [(ne_lng, ne_lat, sw_lng, sw_lat), ...]
    """
    # 서울시 대략적인 경계
    # 남서쪽: (126.7, 37.4)
    # 북동쪽: (127.2, 37.7)
    seoul_sw_lng = 126.7
    seoul_sw_lat = 37.4
    seoul_ne_lng = 127.2
    seoul_ne_lat = 37.7
    
    # 격자 크기를 도 단위로 변환
    grid_size_deg = grid_size_km / 111.0
    
    bboxes = []
    
    # 격자 생성
    current_lat = seoul_sw_lat
    while current_lat < seoul_ne_lat:
        current_lng = seoul_sw_lng
        while current_lng < seoul_ne_lng:
            # 각 격자 셀의 bbox
            ne_lng = current_lng + grid_size_deg
            ne_lat = current_lat + grid_size_deg
            sw_lng = current_lng
            sw_lat = current_lat
            
            bboxes.append((ne_lng, ne_lat, sw_lng, sw_lat))
            
            current_lng += grid_size_deg
        
        current_lat += grid_size_deg
    
    return bboxes


def get_seoul_major_regions() -> List[Tuple[str, float, float]]:
    """서울시 주요 지역 리스트 (지역명, 경도, 위도).
    
    Returns:
        [(지역명, 경도, 위도), ...] 리스트
    """
    return [
        ("강남구", 127.047, 37.517),
        ("서초구", 127.032, 37.483),
        ("송파구", 127.105, 37.514),
        ("강동구", 127.123, 37.530),
        ("광진구", 127.085, 37.538),
        ("성동구", 127.040, 37.563),
        ("중구", 126.997, 37.564),
        ("용산구", 126.978, 37.532),
        ("마포구", 126.902, 37.566),
        ("서대문구", 126.936, 37.579),
        ("은평구", 126.930, 37.602),
        ("종로구", 126.978, 37.573),
        ("성북구", 127.016, 37.589),
        ("강북구", 127.025, 37.639),
        ("도봉구", 127.045, 37.668),
        ("노원구", 127.057, 37.654),
        ("중랑구", 127.094, 37.606),
        ("동대문구", 127.040, 37.574),
        ("영등포구", 126.905, 37.526),
        ("금천구", 126.902, 37.456),
        ("관악구", 126.952, 37.478),
        ("동작구", 126.940, 37.512),
        ("강서구", 126.849, 37.550),
        ("양천구", 126.866, 37.517),
        ("구로구", 126.887, 37.495),
    ]


def get_gu_coordinates(gu_name: str) -> Optional[Tuple[float, float]]:
    """구 이름으로 좌표 가져오기.
    
    Args:
        gu_name: 구 이름 (예: "성동구")
    
    Returns:
        (경도, 위도) 튜플 또는 None
    """
    regions = get_seoul_major_regions()
    for name, lng, lat in regions:
        if name == gu_name or gu_name in name or name in gu_name:
            return (lng, lat)
    return None


async def move_map_to_coordinates(page: Page, lng: float, lat: float, zoom: int = 15, max_attempts: int = 5):
    """지도를 특정 좌표로 이동 (여러 방법 시도).
    
    Args:
        page: Playwright Page 객체
        lng: 경도 (longitude)
        lat: 위도 (latitude)
        zoom: 줌 레벨 (기본값: 15)
        max_attempts: 최대 시도 횟수
    """
    logger.info(f"🗺️ 지도를 좌표로 이동: ({lng}, {lat}), 줌 레벨: {zoom}")
    
    tolerance = 0.01  # 좌표 허용 오차 (약 1km)
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"  시도 {attempt}/{max_attempts}...")
        
        try:
            # 방법 1: 검색창에 좌표나 주소 입력
            try:
                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="검색"]',
                    'input[placeholder*="지역"]',
                    '.search-input',
                    '#search',
                    'input[class*="search"]'
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        search_input = await page.wait_for_selector(selector, timeout=2000)
                        if search_input:
                            # 좌표를 주소 형식으로 변환하여 검색
                            coord_text = f"{lat},{lng}"
                            logger.info(f"    검색창에 좌표 입력: {coord_text}")
                            await search_input.click()
                            await asyncio.sleep(0.5)
                            await search_input.fill(coord_text)
                            await asyncio.sleep(1)
                            await page.keyboard.press('Enter')
                            await asyncio.sleep(3)
                            logger.info("    ✓ 검색창으로 좌표 이동 시도")
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"    검색창 방법 실패: {e}")
            
            # 방법 2: JavaScript로 지도 객체에 직접 접근 (강화)
            try:
                # 모든 가능한 지도 객체 찾기
                map_move_scripts = [
                    # OpenLayers - 다양한 변수명 시도
                    f"""
                    (function() {{
                        // window.map 찾기
                        if (window.map && window.map.getView) {{
                            var view = window.map.getView();
                            view.setCenter(ol.proj.fromLonLat([{lng}, {lat}]));
                            view.setZoom({zoom});
                            return true;
                        }}
                        // 다른 변수명들 시도
                        var mapVars = ['mapInstance', 'olMap', 'mapView', 'mapObj'];
                        for (var i = 0; i < mapVars.length; i++) {{
                            if (window[mapVars[i]] && window[mapVars[i]].getView) {{
                                var view = window[mapVars[i]].getView();
                                view.setCenter(ol.proj.fromLonLat([{lng}, {lat}]));
                                view.setZoom({zoom});
                                return true;
                            }}
                        }}
                        // document에서 찾기
                        var mapElements = document.querySelectorAll('[id*="map"], [class*="map"]');
                        for (var i = 0; i < mapElements.length; i++) {{
                            if (mapElements[i].map && mapElements[i].map.getView) {{
                                var view = mapElements[i].map.getView();
                                view.setCenter(ol.proj.fromLonLat([{lng}, {lat}]));
                                view.setZoom({zoom});
                                return true;
                            }}
                        }}
                        return false;
                    }})();
                    """,
                    # Leaflet
                    f"""
                    (function() {{
                        if (window.map && window.map.setView) {{
                            window.map.setView([{lat}, {lng}], {zoom});
                            return true;
                        }}
                        var mapVars = ['mapInstance', 'leafletMap', 'mapView'];
                        for (var i = 0; i < mapVars.length; i++) {{
                            if (window[mapVars[i]] && window[mapVars[i]].setView) {{
                                window[mapVars[i]].setView([{lat}, {lng}], {zoom});
                                return true;
                            }}
                        }}
                        return false;
                    }})();
                    """,
                    # 일반적인 지도 API
                    f"""
                    (function() {{
                        if (window.map && window.map.setCenter) {{
                            window.map.setCenter([{lat}, {lng}]);
                            if (window.map.setZoom) window.map.setZoom({zoom});
                            return true;
                        }}
                        if (window.map && window.map.panTo) {{
                            window.map.panTo([{lat}, {lng}]);
                            if (window.map.setZoom) window.map.setZoom({zoom});
                            return true;
                        }}
                        return false;
                    }})();
                    """
                ]
                
                for script in map_move_scripts:
                    try:
                        result = await page.evaluate(script)
                        if result:
                            await asyncio.sleep(2)
                            logger.info("    ✓ JavaScript로 지도 이동 시도")
                            break
                    except Exception as e:
                        logger.debug(f"    JavaScript 실행 실패: {e}")
                        continue
            except Exception as e:
                logger.debug(f"    JavaScript 지도 이동 실패: {e}")
            
            # 방법 3: 마우스 드래그 시뮬레이션 (개선된 버전)
            try:
                current_center = await get_current_map_center(page)
                if current_center:
                    current_lng, current_lat = current_center
                    lng_diff = lng - current_lng
                    lat_diff = lat - current_lat
                    
                    if abs(lng_diff) > 0.001 or abs(lat_diff) > 0.001:
                        success = await simulate_mouse_drag_to_location(page, lng, lat, steps=30)
                        if success:
                            logger.info("    ✓ 마우스 드래그로 이동 성공")
                        else:
                            logger.info("    ⚠️ 마우스 드래그로 이동 시도 (부분 성공)")
            except Exception as e:
                logger.debug(f"    마우스 드래그 실패: {e}")
            
            # 방법 3-2: 주소 검색으로 이동 (지역명만 사용)
            try:
                # 좌표 형식은 사용하지 않고, 지역명만 사용
                # 실제로는 region_name 파라미터를 받아서 사용하는 것이 좋음
                address = "성수동"  # 기본값
                await search_address_and_move(page, address)
            except Exception as e:
                logger.debug(f"    주소 검색 실패: {e}")
            
            # 방법 4: URL에 좌표 파라미터 추가 후 새로고침
            try:
                current_url = page.url
                if '?' not in current_url:
                    url_with_coords = f"{current_url}?lng={lng}&lat={lat}&zoom={zoom}"
                else:
                    url_with_coords = f"{current_url}&lng={lng}&lat={lat}&zoom={zoom}"
                
                await page.goto(url_with_coords, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)
                logger.info("    ✓ URL 파라미터로 좌표 이동 시도")
            except Exception as e:
                logger.debug(f"    URL 파라미터 방법 실패: {e}")
            
            # 이동 확인
            await asyncio.sleep(2)
            new_center = await get_current_map_center(page)
            if new_center:
                new_lng, new_lat = new_center
                lng_diff = abs(new_lng - lng)
                lat_diff = abs(new_lat - lat)
                
                if lng_diff < tolerance and lat_diff < tolerance:
                    logger.info(f"  ✅ 지도 이동 성공! 현재 중심: ({new_lng:.4f}, {new_lat:.4f})")
                    return True
                else:
                    logger.info(f"  ⚠️ 지도 이동 미완료. 현재 중심: ({new_lng:.4f}, {new_lat:.4f}), 목표: ({lng:.4f}, {lat:.4f})")
                    logger.info(f"     차이: 경도 {lng_diff:.4f}, 위도 {lat_diff:.4f}")
            else:
                logger.warning("  ⚠️ 현재 지도 중심 좌표를 확인할 수 없습니다.")
            
        except Exception as e:
            logger.debug(f"  시도 {attempt} 실패: {e}")
        
        if attempt < max_attempts:
            await asyncio.sleep(2)
    
    logger.warning("  ⚠️ 자동 좌표 이동 실패. 수동으로 지도를 이동해주세요.")
    logger.info("  💡 브라우저에서 직접 지도를 드래그하여 성수동으로 이동해주세요.")
    logger.info("  ⏳ 20초 대기 중... (수동 이동 시간)")
    await asyncio.sleep(20)
    return False


async def auto_login(page: Page, username: str = "Samwooconc_2", password: str = "Samwooconc_##$$"):
    """OpenUp 웹사이트에 자동으로 로그인.
    
    Args:
        page: Playwright Page 객체
        username: 로그인 아이디
        password: 로그인 비밀번호
    """
    logger.info("🔐 자동 로그인 시도 중...")
    
    try:
        # 로그인 페이지 확인
        current_url = page.url
        if 'login' not in current_url.lower():
            # 로그인 버튼이나 링크 찾기
            login_selectors = [
                'a[href*="login"]',
                'button:has-text("로그인")',
                '.login-button',
                '#login',
                '[class*="login"]'
            ]
            
            login_link = None
            for selector in login_selectors:
                try:
                    login_link = await page.wait_for_selector(selector, timeout=2000)
                    if login_link:
                        logger.info("  로그인 링크 발견, 클릭 중...")
                        await login_link.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
        
        # 로그인 폼 찾기 및 입력
        await asyncio.sleep(2)  # 페이지 로딩 대기
        
        # 아이디 입력 필드 찾기
        username_selectors = [
            'input[name="username"]',
            'input[name="id"]',
            'input[name="email"]',
            'input[type="text"]',
            'input[placeholder*="아이디"]',
            'input[placeholder*="ID"]',
            'input[placeholder*="이메일"]',
            '#username',
            '#id',
            '#email',
            '.username',
            '.id'
        ]
        
        username_input = None
        for selector in username_selectors:
            try:
                username_input = await page.wait_for_selector(selector, timeout=2000)
                if username_input:
                    logger.info("  아이디 입력 필드 발견")
                    break
            except:
                continue
        
        # 비밀번호 입력 필드 찾기
        password_selectors = [
            'input[name="password"]',
            'input[name="pwd"]',
            'input[type="password"]',
            'input[placeholder*="비밀번호"]',
            'input[placeholder*="Password"]',
            '#password',
            '#pwd',
            '.password'
        ]
        
        password_input = None
        for selector in password_selectors:
            try:
                password_input = await page.wait_for_selector(selector, timeout=2000)
                if password_input:
                    logger.info("  비밀번호 입력 필드 발견")
                    break
            except:
                continue
        
        # 로그인 시도
        if username_input and password_input:
            logger.info("  로그인 정보 입력 중...")
            await username_input.fill(username)
            await asyncio.sleep(0.5)
            await password_input.fill(password)
            await asyncio.sleep(0.5)
            
            # 로그인 버튼 찾기 및 클릭
            login_button_selectors = [
                'button[type="submit"]',
                'button:has-text("로그인")',
                'input[type="submit"]',
                'button.login',
                '.login-button',
                '#login-button',
                'button[class*="login"]'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await page.wait_for_selector(selector, timeout=2000)
                    if login_button:
                        logger.info("  로그인 버튼 클릭 중...")
                        await login_button.click()
                        await asyncio.sleep(3)  # 로그인 처리 대기
                        break
                except:
                    continue
            
            # 로그인 성공 확인
            await asyncio.sleep(2)
            new_url = page.url
            if 'login' not in new_url.lower():
                logger.info("  ✓ 로그인 성공!")
                return True
            else:
                logger.warning("  ⚠️ 로그인 실패 또는 로그인 페이지에 여전히 있음")
                logger.info("  ⏳ 10초 대기 중... (수동 로그인 시간)")
                await asyncio.sleep(10)
                return False
        else:
            logger.warning("  ⚠️ 로그인 폼을 찾을 수 없습니다. 수동 로그인이 필요할 수 있습니다.")
            logger.info("  ⏳ 10초 대기 중... (수동 로그인 시간)")
            await asyncio.sleep(10)
            return False
            
    except Exception as e:
        logger.warning(f"  ⚠️ 자동 로그인 중 오류 발생: {e}")
        logger.info("  ⏳ 10초 대기 중... (수동 로그인 시간)")
        await asyncio.sleep(10)
        return False


async def explore_map_region(
    page: Page, 
    region_name: str = "서울",
    coordinates: Optional[Tuple[float, float]] = None,
    bbox_coords: Optional[Tuple[float, float, float, float]] = None,
    zoom: int = 15,
    radius: float = 1.5
):
    """지도를 탐색하여 다양한 영역의 cell-tokens 수집.
    
    Args:
        page: Playwright Page 객체
        region_name: 탐색할 지역명 (검색에 사용)
        coordinates: (경도, 위도) 튜플. 지정하면 해당 좌표로 지도 이동
        bbox_coords: (ne_lng, ne_lat, sw_lng, sw_lat) 튜플. bbox로 지도 이동
        zoom: 초기 줌 레벨 (기본값: 15)
        radius: 중심 좌표 기준 반경 (km)
    """
    logger.info(f"\n📍 지도 탐색 시작: {region_name}")
    if bbox_coords:
        logger.info(f"   bbox: NE({bbox_coords[0]}, {bbox_coords[1]}), SW({bbox_coords[2]}, {bbox_coords[3]})")
    elif coordinates:
        logger.info(f"   좌표: ({coordinates[0]}, {coordinates[1]}), 반경: {radius}km")
    
    try:
        # OpenUp 웹사이트 접속
        logger.info(f"🌐 {OPENUP_URL} 접속 중...")
        await page.goto(OPENUP_URL, wait_until='networkidle', timeout=60000)
        logger.info("페이지 로드 완료. 네트워크 모니터링 시작...")
        await asyncio.sleep(3)  # 페이지 로딩 대기
        
        # 자동 로그인 시도
        await auto_login(page)
        
        # 로그인 후 페이지가 완전히 로드될 때까지 대기 (capture_gp_requests.py 방식)
        logger.info("⏳ 로그인 후 페이지 로드 대기 중...")
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(3)  # 추가 대기 시간
        except Exception as e:
            logger.debug(f"페이지 로드 대기 중: {e}, 계속 진행합니다...")
            await asyncio.sleep(3)
        
        logger.info("✓ 페이지 로드 완료. 지도 탐색 시작...")
        
        # bbox 또는 좌표 기반 이동 시도
        if bbox_coords:
            ne_lng, ne_lat, sw_lng, sw_lat = bbox_coords
            logger.info("  📍 bbox로 지도 이동 시도 중...")
            await move_map_with_bbox(page, ne_lng, ne_lat, sw_lng, sw_lat, region_name=region_name)
        elif coordinates:
            lng, lat = coordinates
            logger.info(f"  📍 좌표로 지도 이동 시도 중: ({lng}, {lat})")
            ne_lng, ne_lat, sw_lng, sw_lat = calculate_bbox_from_center(lng, lat, radius_km=radius)
            await move_map_with_bbox(page, ne_lng, ne_lat, sw_lng, sw_lat, region_name=region_name)
        
        # 지도 탐색 시작 (더 적극적인 실시간 탐색)
        logger.info("")
        logger.info("=" * 60)
        logger.info("🗺️ 실시간 지도 탐색 시작")
        logger.info("=" * 60)
        if region_name:
            logger.info(f"  목표 지역: {region_name}")
        if bbox_coords:
            logger.info(f"  목표 bbox: NE({bbox_coords[0]}, {bbox_coords[1]}), SW({bbox_coords[2]}, {bbox_coords[3]})")
        elif coordinates:
            logger.info(f"  목표 좌표: ({coordinates[0]}, {coordinates[1]})")
        logger.info("")
        logger.info("  📌 지도를 계속 이동하면서 실시간으로 hashkey를 수집합니다.")
        logger.info("")
        
        # 초기 대기 (페이지 로딩 대기)
        await asyncio.sleep(3)
        
        # 지역 검색 (좌표가 없을 때만)
        if not coordinates:
            try:
                # 검색창 찾기 (실제 웹사이트 구조에 맞게 수정 필요)
                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="검색"]',
                    'input[placeholder*="지역"]',
                    '.search-input',
                    '#search'
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        search_input = await page.wait_for_selector(selector, timeout=2000)
                        if search_input:
                            break
                    except:
                        continue
                
                if search_input:
                    logger.info(f"🔍 '{region_name}' 검색 중...")
                    await search_input.fill(region_name)
                    await asyncio.sleep(1)
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(3)
            except Exception as e:
                logger.debug(f"검색 기능 사용 불가: {e}")
        
        # 지도 컨테이너 찾기
        map_selectors = [
            '#map',
            '.map',
            '[class*="map"]',
            'canvas'
        ]
        
        map_element = None
        for selector in map_selectors:
            try:
                map_element = await page.wait_for_selector(selector, timeout=3000)
                if map_element:
                    break
            except:
                continue
        
        if not map_element:
            logger.warning("⚠️ 지도 컨테이너를 찾을 수 없습니다.")
            return
        
        # 실시간 지도 탐색: 반복적으로 지도를 이동하면서 hashkey 수집
        logger.info("🔄 실시간 지도 탐색 시작 (지도를 계속 이동합니다)...")
        
        exploration_duration = 120  # 총 탐색 시간 (초)
        exploration_start_time = asyncio.get_event_loop().time()
        iteration_count = 0
        
        while True:
            current_time = asyncio.get_event_loop().time()
            elapsed_time = current_time - exploration_start_time
            
            if elapsed_time >= exploration_duration:
                logger.info(f"⏰ 탐색 시간 종료 (총 {exploration_duration}초, {len(collected_tokens)}개 토큰 수집)")
                break
            
            iteration_count += 1
            logger.info(f"🔄 탐색 반복 {iteration_count} (경과: {elapsed_time:.0f}초, 수집된 토큰: {len(collected_tokens)}개)")
            
            try:
                box = await map_element.bounding_box()
                if not box:
                    await asyncio.sleep(1)
                    continue
                
                center_x = box['width'] / 2
                center_y = box['height'] / 2
                
                # 지도를 다양한 방향으로 드래그 (더 넓은 범위)
                drag_distances = [200, 300, 400]  # 다양한 거리로 드래그
                
                for distance in drag_distances:
                    directions = [
                        (center_x, center_y, center_x - distance, center_y),  # 왼쪽
                        (center_x, center_y, center_x + distance, center_y),  # 오른쪽
                        (center_x, center_y, center_x, center_y - distance),  # 위
                        (center_x, center_y, center_x, center_y + distance),  # 아래
                        (center_x, center_y, center_x - distance * 0.7, center_y - distance * 0.7),  # 좌상
                        (center_x, center_y, center_x + distance * 0.7, center_y - distance * 0.7),  # 우상
                        (center_x, center_y, center_x - distance * 0.7, center_y + distance * 0.7),  # 좌하
                        (center_x, center_y, center_x + distance * 0.7, center_y + distance * 0.7),  # 우하
                    ]
                    
                    for start_x, start_y, end_x, end_y in directions:
                        try:
                            await map_element.hover(position={'x': start_x, 'y': start_y})
                            await page.mouse.down()
                            await page.mouse.move(end_x, end_y)
                            await page.mouse.up()
                            await asyncio.sleep(1)  # 각 이동 후 짧은 대기 (API 요청 대기)
                            
                            # 수집된 토큰 수 확인
                            if len(collected_tokens) > 0 and iteration_count % 5 == 0:
                                logger.info(f"  ✓ 현재까지 {len(collected_tokens)}개 토큰 수집됨")
                        except Exception as e:
                            logger.debug(f"드래그 실패: {e}")
                            continue
                
                # 줌 인/아웃 (다양한 줌 레벨 탐색)
                if iteration_count % 10 == 0:
                    try:
                        await map_element.hover()
                        # 줌 인
                        await page.mouse.wheel(0, -200)
                        await asyncio.sleep(1.5)
                        # 줌 아웃
                        await page.mouse.wheel(0, 200)
                        await asyncio.sleep(1.5)
                        logger.info(f"  🔍 줌 조작 완료 (토큰: {len(collected_tokens)}개)")
                    except Exception as e:
                        logger.debug(f"줌 조작 실패: {e}")
                
                # 지도 클릭 (다양한 위치)
                if iteration_count % 8 == 0:
                    positions = [
                        {'x': box['width'] * 0.25, 'y': box['height'] * 0.25},  # 좌상
                        {'x': box['width'] * 0.75, 'y': box['height'] * 0.25},  # 우상
                        {'x': box['width'] * 0.25, 'y': box['height'] * 0.75},  # 좌하
                        {'x': box['width'] * 0.75, 'y': box['height'] * 0.75},  # 우하
                        {'x': box['width'] * 0.5, 'y': box['height'] * 0.5},    # 중앙
                    ]
                    
                    for pos in positions:
                        try:
                            await map_element.click(position=pos)
                            await asyncio.sleep(1)
                        except:
                            pass
                
                # 짧은 대기 (API 요청 처리 시간 확보)
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"탐색 반복 중 오류: {e}")
                await asyncio.sleep(1)
                continue
        
        # 최종 대기 (마지막 API 요청 완료 대기)
        logger.info(f"⏳ 최종 대기 중... (현재까지 {len(collected_tokens)}개 토큰 수집)")
        await asyncio.sleep(5)
        
        # 건물 마커 클릭 시도 (있는 경우)
        logger.info("🏢 건물 마커 클릭 시도 중...")
        marker_selectors = [
            '[class*="marker"]',
            '[class*="building"]',
            '.marker',
            'div[style*="position: absolute"]'
        ]
        
        for selector in marker_selectors:
            try:
                markers = await page.query_selector_all(selector)
                if markers:
                    logger.info(f"  {len(markers)}개 마커 발견, 일부 클릭 시도...")
                    for i, marker in enumerate(markers[:10]):  # 처음 10개만
                        try:
                            await marker.click(timeout=1000)
                            await asyncio.sleep(1)
                        except:
                            pass
                    break
            except:
                continue
        
        # 추가 대기 시간 (API 요청 완료 대기)
        logger.info("⏳ 추가 API 요청 대기 중... (10초)")
        await asyncio.sleep(10)
        
    except Exception as e:
        logger.error(f"지도 탐색 중 오류 발생: {e}")
        import traceback
        logger.debug(traceback.format_exc())


async def explore_seoul_systematically(
    page: Page,
    grid_size_km: float = 2.0,
    use_major_regions: bool = True
) -> None:
    """서울시 전체를 체계적으로 탐색하여 cell-tokens 수집.
    
    Args:
        page: Playwright Page 객체
        grid_size_km: 격자 크기 (km)
        use_major_regions: 주요 지역 우선 탐색 여부
    """
    logger.info("=" * 60)
    logger.info("🗺️ 서울시 전체 체계적 탐색 시작")
    logger.info("=" * 60)
    
    if use_major_regions:
        logger.info("📍 주요 지역 우선 탐색 모드")
        regions = get_seoul_major_regions()
        logger.info(f"   총 {len(regions)}개 주요 지역 탐색 예정")
        
        for idx, (region_name, lng, lat) in enumerate(regions, 1):
            logger.info(f"\n[{idx}/{len(regions)}] {region_name} 탐색 중...")
            logger.info(f"   좌표: ({lng}, {lat})")
            
            # 해당 지역으로 이동 시도
            ne_lng, ne_lat, sw_lng, sw_lat = calculate_bbox_from_center(lng, lat, radius_km=grid_size_km/2)
            await move_map_with_bbox(page, ne_lng, ne_lat, sw_lng, sw_lat, region_name=region_name)
            
            # 주소 검색으로 이동
            await search_address_and_move(page, region_name)
            await asyncio.sleep(2)
            
            # 지도 클릭/드래그로 탐색
            try:
                map_element = await page.wait_for_selector('#map, .map, [class*="map"], canvas', timeout=3000)
                if map_element:
                    box = await map_element.bounding_box()
                    if box:
                        # 중앙 클릭
                        center_x = box['width'] / 2
                        center_y = box['height'] / 2
                        await map_element.click(position={'x': center_x, 'y': center_y})
                        await asyncio.sleep(1)
                        
                        # 4방향 드래그
                        drag_movements = [
                            (center_x, center_y, center_x - 50, center_y),  # 왼쪽
                            (center_x, center_y, center_x + 50, center_y),  # 오른쪽
                            (center_x, center_y, center_x, center_y - 50),  # 위
                            (center_x, center_y, center_x, center_y + 50),  # 아래
                        ]
                        
                        for start_x, start_y, end_x, end_y in drag_movements:
                            try:
                                await map_element.hover(position={'x': start_x, 'y': start_y})
                                await page.mouse.down()
                                await page.mouse.move(end_x, end_y)
                                await page.mouse.up()
                                await asyncio.sleep(1)
                            except:
                                pass
            except:
                pass
            
            # 각 지역마다 짧은 대기 (Network 요청 수집)
            await asyncio.sleep(2)
    
    # 격자 기반 추가 탐색
    logger.info("\n📍 격자 기반 추가 탐색 시작")
    bboxes = generate_seoul_grid(grid_size_km)
    logger.info(f"   총 {len(bboxes)}개 격자 생성")
    logger.info("   ⚠️ 격자 탐색은 시간이 오래 걸릴 수 있습니다.")
    logger.info("   💡 중단하려면 Ctrl+C를 누르세요.")
    
    for idx, (ne_lng, ne_lat, sw_lng, sw_lat) in enumerate(bboxes, 1):
        if idx % 10 == 0:
            logger.info(f"   진행: {idx}/{len(bboxes)} 격자 탐색 완료 (현재까지 수집된 cell-tokens: {len(collected_tokens)}개)")
        
        # bbox로 이동 시도
        center_lng = (ne_lng + sw_lng) / 2
        center_lat = (ne_lat + sw_lat) / 2
        await move_map_with_bbox(page, ne_lng, ne_lat, sw_lng, sw_lat)
        
        # 짧은 대기 (Network 요청 수집)
        await asyncio.sleep(1)
        
        # 일정 간격으로 지도 클릭
        if idx % 5 == 0:
            try:
                map_element = await page.wait_for_selector('#map, .map, [class*="map"], canvas', timeout=2000)
                if map_element:
                    box = await map_element.bounding_box()
                    if box:
                        center_x = box['width'] / 2
                        center_y = box['height'] / 2
                        await map_element.click(position={'x': center_x, 'y': center_y})
                        await asyncio.sleep(1)
            except:
                pass


async def collect_cell_tokens(
    region: str = "서울",
    headless: bool = False,
    timeout: int = 300,
    coordinates: Optional[Tuple[float, float]] = None,
    bbox_coords: Optional[Tuple[float, float, float, float]] = None,
    zoom: int = 15,
    radius: float = 1.5,
    explore_seoul: bool = False,
    explore_gu: Optional[str] = None,
    grid_size: float = 2.0
) -> Tuple[Set[str], Set[str]]:
    """cell-tokens를 자동으로 수집.
    
    Args:
        region: 탐색할 지역명
        headless: 헤드리스 모드 (False면 브라우저 표시)
        timeout: 타임아웃 (초)
        coordinates: (경도, 위도) 튜플. 지정하면 해당 좌표로 지도 이동
        zoom: 초기 줌 레벨 (기본값: 15)
    
    Returns:
        (collected_tokens, collected_access_tokens) 튜플
    """
    global collected_tokens, collected_access_tokens
    
    collected_tokens.clear()
    collected_access_tokens.clear()
    
    async with async_playwright() as p:
        logger.info("🚀 Playwright 브라우저 시작 중...")
        
        # Chromium 브라우저 실행
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 새 컨텍스트 생성 (쿠키, 캐시 등 분리)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 페이지 생성 (핸들러 등록 전)
        page = await context.new_page()
        
        # Network 요청/응답 핸들러 설정 (capture_gp_requests.py 방식)
        await setup_network_handlers(context, page)
        
        try:
            # 특정 구만 탐색 모드
            if explore_gu:
                # OpenUp 웹사이트 접속 및 로그인
                logger.info(f"🌐 {OPENUP_URL} 접속 중...")
                await page.goto(OPENUP_URL, wait_until='networkidle', timeout=60000)
                logger.info("페이지 로드 완료. 네트워크 모니터링 시작...")
                await asyncio.sleep(3)
                await auto_login(page)
                
                # 로그인 후 페이지가 완전히 로드될 때까지 대기
                logger.info("⏳ 로그인 후 페이지 로드 대기 중...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.debug(f"페이지 로드 대기 중: {e}, 계속 진행합니다...")
                    await asyncio.sleep(3)
                logger.info("✓ 페이지 로드 완료.")
                
                # 특정 구만 탐색
                gu_name = explore_gu
                gu_coords = get_gu_coordinates(gu_name)
                if gu_coords:
                    logger.info(f"📍 {gu_name} 탐색 모드")
                    lng, lat = gu_coords
                    ne_lng, ne_lat, sw_lng, sw_lat = calculate_bbox_from_center(lng, lat, radius_km=grid_size/2)
                    await move_map_with_bbox(page, ne_lng, ne_lat, sw_lng, sw_lat, region_name=gu_name)
                    await search_address_and_move(page, gu_name)
                    await asyncio.sleep(2)
                    
                    # 수동 이동 안내 및 대기
                    logger.info("")
                    logger.info("=" * 60)
                    logger.info("💡 중요: 지도 수동 이동 가능")
                    logger.info("=" * 60)
                    logger.info(f"  목표 지역: {gu_name}")
                    logger.info(f"  목표 좌표: ({lng}, {lat})")
                    logger.info("")
                    logger.info("  📌 브라우저에서 지도를 직접 드래그하여 탐색하세요.")
                    logger.info("  📌 지도를 이동하면 Network에서 coord 요청이 발생하고,")
                    logger.info("     그때 해당 영역의 cell-tokens가 자동으로 수집됩니다.")
                    logger.info("")
                    logger.info("  ⏳ 30초 대기 중... (지도를 이동하고 탐색하세요)")
                    await asyncio.sleep(30)
                    
                    # 추가 대기 시간 (API 요청 완료 대기)
                    logger.info("⏳ 추가 API 요청 대기 중... (10초)")
                    await asyncio.sleep(10)
                    
                    logger.info(f"   ✅ {gu_name} 탐색 완료! 총 {len(collected_tokens)}개 cell-tokens 수집")
                else:
                    logger.warning(f"⚠️ {gu_name}의 좌표를 찾을 수 없습니다.")
            # 서울시 전체 탐색 모드
            elif explore_seoul:
                # OpenUp 웹사이트 접속 및 로그인
                logger.info(f"🌐 {OPENUP_URL} 접속 중...")
                await page.goto(OPENUP_URL, wait_until='networkidle', timeout=60000)
                logger.info("페이지 로드 완료. 네트워크 모니터링 시작...")
                await asyncio.sleep(3)
                await auto_login(page)
                
                # 로그인 후 페이지가 완전히 로드될 때까지 대기
                logger.info("⏳ 로그인 후 페이지 로드 대기 중...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.debug(f"페이지 로드 대기 중: {e}, 계속 진행합니다...")
                    await asyncio.sleep(3)
                logger.info("✓ 페이지 로드 완료.")
                
                # 서울시 전체 체계적 탐색
                await explore_seoul_systematically(page, grid_size_km=grid_size, use_major_regions=True)
            else:
                # 일반 지도 탐색
                await explore_map_region(page, region, coordinates, bbox_coords, zoom, radius)
            
            # 최종 대기 (모든 요청 완료 대기)
            logger.info("⏳ 최종 대기 중... (5초)")
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"수집 중 오류 발생: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            await browser.close()
    
    return collected_tokens, collected_access_tokens


def load_existing_tokens(token_file_path: Path) -> Tuple[Optional[str], Set[str]]:
    """기존 토큰 파일에서 cell-tokens와 access-token 로드.
    
    Args:
        token_file_path: 토큰 파일 경로
    
    Returns:
        (access_token, cell_tokens_set) 튜플
    """
    if not token_file_path.exists():
        return None, set()
    
    content = token_file_path.read_text(encoding='utf-8')
    
    # access-token 추출
    access_token_match = re.search(r'OPENUP_ACCESS_TOKEN\s*=\s*([a-f0-9-]+)', content)
    access_token = access_token_match.group(1) if access_token_match else None
    
    # cell_tokens 추출
    tokens = re.findall(r'"([a-f0-9]{8})"', content)
    unique_tokens = set(tokens)
    
    return access_token, unique_tokens


def save_tokens(
    tokens: Set[str],
    access_tokens: Set[str],
    output_file: Path,
    existing_access_token: Optional[str] = None
):
    """수집된 cell-tokens를 파일로 저장.
    
    Args:
        tokens: 수집된 cell-tokens
        access_tokens: 수집된 access-tokens
        output_file: 출력 파일 경로
        existing_access_token: 기존 access-token (우선 사용)
    """
    # Access-token 선택 (기존 것이 있으면 사용, 없으면 수집된 것 중 첫 번째)
    access_token = existing_access_token
    if not access_token and access_tokens:
        access_token = list(access_tokens)[0]
    
    # 날짜 형식
    date_str = datetime.now().strftime("%Y%m%d")
    
    # 파일 내용 작성
    lines = [
        f"# {date_str}",
        "# access-token",
    ]
    
    if access_token:
        lines.append(f"OPENUP_ACCESS_TOKEN = {access_token}")
    else:
        lines.append("# OPENUP_ACCESS_TOKEN = (수집되지 않음)")
    
    lines.append("")
    lines.append("# cell_tokens")
    
    # cell-tokens 정렬하여 추가
    sorted_tokens = sorted(tokens)
    for token in sorted_tokens:
        lines.append(f'"{token}",')
    
    # 파일 저장
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text('\n'.join(lines), encoding='utf-8')
    
    logger.info(f"💾 토큰 파일 저장 완료: {output_file}")
    logger.info(f"   - Access-token: {'수집됨' if access_token else '수집 안됨'}")
    logger.info(f"   - Cell-tokens: {len(sorted_tokens)}개")


def main():
    """메인 실행 함수."""
    parser = argparse.ArgumentParser(
        description='OpenUp 웹사이트를 자동으로 탐색하여 cell-tokens 수집'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='서울',
        help='탐색할 지역명 (기본값: 서울)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='출력 파일명 (기본값: {날짜}_token)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='헤드리스 모드 (브라우저 숨김)'
    )
    parser.add_argument(
        '--merge',
        type=str,
        default=None,
        help='기존 토큰 파일과 병합할 파일 경로'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='타임아웃 (초, 기본값: 300)'
    )
    parser.add_argument(
        '--lng',
        type=float,
        default=None,
        help='경도 (longitude). 지정하면 해당 좌표로 지도 이동'
    )
    parser.add_argument(
        '--lat',
        type=float,
        default=None,
        help='위도 (latitude). 지정하면 해당 좌표로 지도 이동'
    )
    parser.add_argument(
        '--zoom',
        type=int,
        default=15,
        help='초기 줌 레벨 (기본값: 15)'
    )
    parser.add_argument(
        '--bbox',
        type=str,
        default=None,
        help='bbox 형식: "ne_lng,ne_lat,sw_lng,sw_lat" (예: "127.06,37.55,127.04,37.53")'
    )
    parser.add_argument(
        '--radius',
        type=float,
        default=1.5,
        help='중심 좌표 기준 반경 (km, 기본값: 1.5)'
    )
    parser.add_argument(
        '--explore-seoul',
        action='store_true',
        help='서울시 전체를 체계적으로 탐색 (격자 기반)'
    )
    parser.add_argument(
        '--explore-gu',
        type=str,
        default=None,
        help='특정 구만 탐색 (예: "성동구", "강남구")'
    )
    parser.add_argument(
        '--grid-size',
        type=float,
        default=2.0,
        help='격자 크기 (km, 기본값: 2.0)'
    )
    
    args = parser.parse_args()
    
    # 좌표 또는 bbox 검증
    coordinates = None
    bbox_coords = None
    
    if args.bbox:
        # bbox 형식 파싱: "ne_lng,ne_lat,sw_lng,sw_lat"
        try:
            parts = [float(x.strip()) for x in args.bbox.split(',')]
            if len(parts) != 4:
                raise ValueError("bbox는 4개의 값이 필요합니다")
            bbox_coords = (parts[0], parts[1], parts[2], parts[3])  # ne_lng, ne_lat, sw_lng, sw_lat
            logger.info(f"📦 bbox 사용: NE({parts[0]}, {parts[1]}), SW({parts[2]}, {parts[3]})")
        except Exception as e:
            logger.error(f"❌ bbox 형식 오류: {e}")
            logger.error("   형식: --bbox \"ne_lng,ne_lat,sw_lng,sw_lat\"")
            sys.exit(1)
    elif args.lng is not None or args.lat is not None:
        if args.lng is None or args.lat is None:
            logger.error("❌ --lng와 --lat은 함께 지정해야 합니다.")
            sys.exit(1)
        if not (-180 <= args.lng <= 180) or not (-90 <= args.lat <= 90):
            logger.error("❌ 좌표 범위가 올바르지 않습니다. (경도: -180~180, 위도: -90~90)")
            sys.exit(1)
        coordinates = (args.lng, args.lat)
    
    # 출력 파일명 결정
    if args.output:
        output_filename = args.output
    else:
        date_str = datetime.now().strftime("%y%m%d")
        output_filename = f"{date_str}_token"
    
    output_file = project_root / "docs" / "sources" / "openup" / "raw" / output_filename
    
    # 기존 토큰 로드 (병합용)
    existing_access_token = None
    existing_tokens = set()
    
    if args.merge:
        merge_file = Path(args.merge)
        if merge_file.exists():
            existing_access_token, existing_tokens = load_existing_tokens(merge_file)
            logger.info(f"📂 기존 토큰 파일 로드: {len(existing_tokens)}개 cell-tokens")
        else:
            logger.warning(f"⚠️ 병합할 파일을 찾을 수 없습니다: {merge_file}")
    elif output_file.exists():
        existing_access_token, existing_tokens = load_existing_tokens(output_file)
        logger.info(f"📂 기존 토큰 파일 로드: {len(existing_tokens)}개 cell-tokens")
    
    # cell-tokens 수집
    logger.info("=" * 60)
    logger.info("🔍 OpenUp Cell-Token 자동 수집 시작")
    logger.info("=" * 60)
    
    if not args.headless:
        logger.info("💡 브라우저가 열립니다. 필요시 수동으로 로그인해주세요.")
    
    try:
        collected_tokens, collected_access_tokens = asyncio.run(
            collect_cell_tokens(
                region=args.region,
                headless=args.headless,
                timeout=args.timeout,
                coordinates=coordinates,
                bbox_coords=bbox_coords,
                zoom=args.zoom,
                radius=args.radius,
                explore_seoul=args.explore_seoul,
                explore_gu=args.explore_gu,
                grid_size=args.grid_size
            )
        )
        
        # 기존 토큰과 병합
        all_tokens = existing_tokens.union(collected_tokens)
        
        logger.info("=" * 60)
        logger.info("📊 수집 결과")
        logger.info("=" * 60)
        logger.info(f"   기존 cell-tokens: {len(existing_tokens)}개")
        logger.info(f"   새로 수집된 cell-tokens: {len(collected_tokens)}개")
        logger.info(f"   총 cell-tokens: {len(all_tokens)}개")
        logger.info(f"   수집된 access-tokens: {len(collected_access_tokens)}개")
        
        # 파일 저장
        save_tokens(
            tokens=all_tokens,
            access_tokens=collected_access_tokens,
            output_file=output_file,
            existing_access_token=existing_access_token
        )
        
        logger.info("=" * 60)
        logger.info("✅ Cell-Token 수집 완료!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 사용자에 의해 중단되었습니다.")
        # 중단 전까지 수집된 것 저장
        if collected_tokens or existing_tokens:
            all_tokens = existing_tokens.union(collected_tokens)
            save_tokens(
                tokens=all_tokens,
                access_tokens=collected_access_tokens,
                output_file=output_file,
                existing_access_token=existing_access_token
            )
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
