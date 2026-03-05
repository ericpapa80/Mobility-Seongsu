# V-world WFS 2.0 이관 가이드

다른 프로젝트에 V-world WFS 2.0 API를 구현하기 위한 최소 구성 요소 및 이관 방법입니다.

## 📋 목차

1. [필수 구성 요소](#필수-구성-요소)
2. [설치 방법](#설치-방법)
3. [사용 예제](#사용-예제)
4. [API 엔드포인트](#api-엔드포인트)
5. [주의사항](#주의사항)

---

## 필수 구성 요소

### 1. 환경 변수 설정

**`.env` 파일** (프로젝트 루트에 생성)

```env
vworld_api_key=YOUR_API_KEY
vworld_domain=http://localhost
```

- `vworld_api_key`: vworld 개발자센터에서 발급받은 인증키
- `vworld_domain`: vworld 개발자센터에 등록한 도메인 (예: `http://localhost`, `https://yourdomain.com`)

### 2. API 엔드포인트

- **WFS**: `https://api.vworld.kr/req/wfs?`
- **Data API**: `https://api.vworld.kr/req/data?` (권장)

### 3. 의존성

**필수 라이브러리 없음** - 순수 JavaScript/jQuery로 구현 가능

선택적:
- jQuery (JSONP 요청용)
- OpenLayers (지도 표시용, 선택)

---

## 설치 방법

### 1단계: 환경 변수 파일 복사

```bash
# .env_sample을 .env로 복사
cp .env_sample .env

# .env 파일 편집하여 본인의 API 키와 도메인 입력
```

### 2단계: 예제 코드 복사

다음 파일들을 새 프로젝트에 복사:
- `examples/wfs-example.html` (WFS 예제)
- `examples/data-api-example.html` (Data API 예제)
- `examples/vworld-wfs-helper.js` (헬퍼 함수, 선택)

### 3단계: 코드 통합

프로젝트에 맞게 예제 코드를 수정하여 통합합니다.

---

## 사용 예제

### 방법 1: WFS API (req/wfs)

```javascript
// WFS GetFeature 요청
const apiKey = 'YOUR_API_KEY';
const domain = 'http://localhost';

$.ajax({
    url: 'https://api.vworld.kr/req/wfs?',
    type: 'GET',
    dataType: 'jsonp',
    data: {
        service: 'WFS',
        request: 'GetFeature',
        TYPENAME: 'lt_c_landinfobasemap',  // 레이어 ID
        bbox: '14134500,4518600,14136500,4520600',  // minX,minY,maxX,maxY
        version: '1.1.0',
        output: 'text/javascript',
        key: apiKey,
        format_options: 'callback:myCallback',
        crs: 'EPSG:3857'
    },
    jsonp: false,
    jsonpCallback: 'myCallback',
    success: function(data) {
        // data.features 배열 처리
        data.features.forEach(feature => {
            console.log(feature.properties);
            console.log(feature.geometry);
        });
    },
    error: function(xhr, status, error) {
        console.error('WFS 요청 실패:', error);
    }
});
```

### 방법 2: Data API (req/data) - 권장

```javascript
// Data API GetFeature 요청
const apiKey = 'YOUR_API_KEY';
const domain = 'http://localhost';

$.ajax({
    url: 'https://api.vworld.kr/req/data?',
    type: 'GET',
    dataType: 'jsonp',
    data: {
        key: apiKey,
        domain: domain,
        service: 'data',
        version: '2.0',
        request: 'GetFeature',
        format: 'json',
        size: 100,
        page: 1,
        geometry: true,
        attribute: true,
        crs: 'EPSG:3857',
        data: 'LT_C_LANDINFOBASEMAP',  // 레이어 ID (대문자)
        geomfilter: 'BOX(14134500,4518600,14136500,4520600)'  // minX,minY,maxX,maxY
    },
    success: function(response) {
        if (response.response.status === 'OK') {
            const features = response.response.result.featureCollection.features;
            features.forEach(feature => {
                console.log('속성:', feature.properties);
                console.log('지오메트리:', feature.geometry);
            });
        } else {
            console.error('에러:', response.response.error);
        }
    },
    error: function(xhr, status, error) {
        console.error('요청 실패:', error);
    }
});
```

### 방법 3: 환경 변수 사용 (Node.js/서버사이드)

```javascript
// .env 파일 로드 (dotenv 패키지 사용)
require('dotenv').config();

const apiKey = process.env.VWORLD_API_KEY;
const domain = process.env.VWORLD_DOMAIN || 'http://localhost';

// fetch 또는 axios로 요청
const url = `https://api.vworld.kr/req/data?key=${apiKey}&domain=${encodeURIComponent(domain)}&service=data&version=2.0&request=GetFeature&format=json&size=100&geometry=true&attribute=true&crs=EPSG:3857&data=LT_C_LANDINFOBASEMAP&geomfilter=BOX(14134500,4518600,14136500,4520600)`;

fetch(url)
    .then(res => res.json())
    .then(data => {
        if (data.response.status === 'OK') {
            console.log('총 건수:', data.response.record.total);
            console.log('피처:', data.response.result.featureCollection.features);
        }
    })
    .catch(err => console.error('에러:', err));
```

---

## API 엔드포인트

### WFS API (`req/wfs`)

**URL**: `https://api.vworld.kr/req/wfs?`

**주요 파라미터**:
- `SERVICE=WFS`
- `REQUEST=GetFeature`
- `TYPENAME`: 레이어 ID (예: `lt_c_landinfobasemap`)
- `BBOX`: 경계 박스 (minX,minY,maxX,maxY)
- `VERSION=1.1.0`
- `KEY`: 인증키
- `DOMAIN`: 등록 도메인
- `OUTPUT`: 출력 형식 (GML2, json 등)

### Data API (`req/data`) - 권장

**URL**: `https://api.vworld.kr/req/data?`

**주요 파라미터**:
- `key`: 인증키
- `domain`: 등록 도메인
- `service=data`
- `version=2.0`
- `request=GetFeature`
- `format=json`
- `size`: 페이지당 건수
- `page`: 페이지 번호
- `geometry=true`: 지오메트리 포함 여부
- `attribute=true`: 속성 포함 여부
- `crs`: 좌표계 (EPSG:3857, EPSG:4326 등)
- `data`: 레이어 ID (대문자, 예: `LT_C_LANDINFOBASEMAP`)
- `geomfilter`: 공간 필터 (BOX, polygon 등)

---

## 주의사항

### 1. 인증키 및 도메인

- **KEY**와 **DOMAIN**은 vworld 개발자센터에 등록된 값과 정확히 일치해야 합니다.
- 도메인은 `http://localhost`, `https://yourdomain.com` 등 정확한 형식으로 입력.
- 포트 번호 포함 여부도 일치해야 함 (예: `http://localhost:8080` vs `http://localhost`).

### 2. geomFilter 제한

- **BOX/polygon 면적은 10km² 이내**여야 합니다.
- 초과 시 `INVALID_RANGE` 오류 발생.

### 3. 레이어 ID 대소문자

- **WFS**: 소문자 (예: `lt_c_landinfobasemap`)
- **Data API**: 대문자 (예: `LT_C_LANDINFOBASEMAP`)

### 4. 좌표계

- `EPSG:3857` (Web Mercator) - 일반적
- `EPSG:4326` (WGS84) - 위경도
- `EPSG:900913` - Google Maps 호환

### 5. CORS/JSONP

- 브라우저에서 직접 호출 시 **JSONP** 사용 필요.
- 서버사이드에서는 일반 HTTP 요청 가능.

---

## 레이어 정보

사용 가능한 레이어 목록 및 컬럼 정보:
- `WFS_2.0/브이월드_WFS_컬럼정보.csv` 참고

주요 레이어 예시:
- `LT_C_LANDINFOBASEMAP` (LX맵)
- `LT_C_SPBD` (도로명주소건물)
- `LP_PA_CBND_BUBUN` (지적도 부번)
- 기타: CSV 파일 참조

---

## 문제 해결

### INCORRECT_KEY 오류

1. vworld 개발자센터에서 키 상태 확인
2. 등록된 도메인 확인
3. KEY·DOMAIN 값이 정확한지 확인

### INVALID_RANGE 오류

- geomFilter BOX 면적이 10km² 초과
- 더 작은 영역으로 요청

### 레이어를 찾을 수 없음

- 레이어 ID 대소문자 확인
- CSV 파일에서 레이어 ID 확인

---

## 참고 자료

- V-world 개발자센터: https://www.vworld.kr/dev/v4dv_wmsguide2_s001.do
- WFS 컬럼 정보: `WFS_2.0/브이월드_WFS_컬럼정보.csv`
- 테스트 결과: `WFS_2.0/WFS.txt`
