# V-world WFS 2.0 빠른 시작 가이드

## 🚀 3단계로 시작하기

### 1단계: 파일 복사

다음 파일들을 새 프로젝트에 복사:

```
WFS_2.0/
├── examples/
│   ├── data-api-example.html      ⭐ (권장)
│   ├── wfs-example.html
│   ├── vworld-wfs-helper.js
│   └── README.md
├── .env_sample
└── MIGRATION_GUIDE.md
```

### 2단계: 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
vworld_api_key=YOUR_API_KEY
vworld_domain=http://localhost
```

**vworld 개발자센터**에서:
1. 인증키 발급
2. 도메인 등록 (예: `http://localhost`, `https://yourdomain.com`)

### 3단계: 코드 통합

#### 방법 A: HTML에서 직접 사용 (가장 간단)

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body>
    <script>
        const apiKey = 'YOUR_API_KEY';
        const domain = 'http://localhost';
        
        $.ajax({
            url: 'https://api.vworld.kr/req/data?',
            dataType: 'jsonp',
            data: {
                key: apiKey,
                domain: domain,
                service: 'data',
                version: '2.0',
                request: 'GetFeature',
                format: 'json',
                size: 10,
                geometry: true,
                attribute: true,
                crs: 'EPSG:3857',
                data: 'LT_C_LANDINFOBASEMAP',  // LX맵
                geomfilter: 'BOX(14134500,4518600,14136500,4520600)'
            },
            success: function(response) {
                if (response.response.status === 'OK') {
                    console.log('총 건수:', response.response.record.total);
                    console.log('피처:', response.response.result.featureCollection.features);
                }
            }
        });
    </script>
</body>
</html>
```

#### 방법 B: 헬퍼 클래스 사용

```html
<script src="vworld-wfs-helper.js"></script>
<script>
    const wfs = new VWorldWFS('YOUR_API_KEY', 'http://localhost');
    
    wfs.getFeatures('LT_C_LANDINFOBASEMAP', [14134500, 4518600, 14136500, 4520600])
        .then(result => {
            if (result.success) {
                console.log('성공:', result.total, '건');
            }
        });
</script>
```

#### 방법 C: Node.js/서버사이드

```javascript
// .env 로드
require('dotenv').config();
const VWorldWFS = require('./vworld-wfs-helper.js');

const { apiKey, domain } = VWorldWFS.loadFromEnv('.env');
const wfs = new VWorldWFS(apiKey, domain);

wfs.getFeatures('LT_C_LANDINFOBASEMAP', [14134500, 4518600, 14136500, 4520600])
    .then(result => {
        if (result.success) {
            console.log('총 건수:', result.total);
        }
    });
```

---

## 📦 최소 필수 파일

다른 프로젝트로 이관 시 **최소한** 필요한 것:

1. **환경 변수**: `.env` 또는 환경 변수 설정
2. **API 엔드포인트**: 
   - `https://api.vworld.kr/req/data?` (Data API - 권장)
   - `https://api.vworld.kr/req/wfs?` (WFS API)
3. **인증 정보**: KEY, DOMAIN

**의존성 없음** - 순수 JavaScript/jQuery로 동작

---

## 🔑 핵심 파라미터

### Data API (권장)

| 파라미터 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `key` | ✅ | 인증키 | `YOUR_API_KEY` |
| `domain` | ✅ | 등록 도메인 | `http://localhost` |
| `service` | ✅ | `data` | `data` |
| `version` | ✅ | `2.0` | `2.0` |
| `request` | ✅ | `GetFeature` | `GetFeature` |
| `data` | ✅ | 레이어 ID (대문자) | `LT_C_LANDINFOBASEMAP` |
| `geomfilter` | ✅ | 공간 필터 | `BOX(14134500,4518600,14136500,4520600)` |
| `size` | | 페이지 크기 | `100` |
| `page` | | 페이지 번호 | `1` |
| `crs` | | 좌표계 | `EPSG:3857` |

### WFS API

| 파라미터 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `KEY` | ✅ | 인증키 | `YOUR_API_KEY` |
| `DOMAIN` | ✅ | 등록 도메인 | `http://localhost` |
| `SERVICE` | ✅ | `WFS` | `WFS` |
| `REQUEST` | ✅ | `GetFeature` | `GetFeature` |
| `TYPENAME` | ✅ | 레이어 ID (소문자) | `lt_c_landinfobasemap` |
| `BBOX` | ✅ | 경계 박스 | `14134500,4518600,14136500,4520600` |
| `VERSION` | ✅ | `1.1.0` | `1.1.0` |

---

## ⚠️ 주의사항

1. **도메인 일치**: vworld 개발자센터에 등록한 도메인과 정확히 일치해야 함
   - ✅ `http://localhost` (등록됨) → `http://localhost` (요청)
   - ❌ `http://localhost` (등록됨) → `http://localhost:8080` (요청) → INCORRECT_KEY

2. **면적 제한**: geomFilter BOX 면적은 **10km² 이내**
   - 초과 시 `INVALID_RANGE` 오류

3. **레이어 ID 대소문자**:
   - WFS: 소문자 (`lt_c_landinfobasemap`)
   - Data API: 대문자 (`LT_C_LANDINFOBASEMAP`)

---

## 📚 더 알아보기

- **상세 가이드**: `MIGRATION_GUIDE.md`
- **예제 파일**: `examples/` 폴더
- **레이어 목록**: `브이월드_WFS_컬럼정보.csv`
- **테스트 결과**: `WFS.txt`

---

## 🆘 문제 해결

| 오류 | 원인 | 해결 |
|------|------|------|
| `INCORRECT_KEY` | KEY/DOMAIN 불일치 | vworld 개발자센터에서 확인 |
| `INVALID_RANGE` | geomFilter 면적 > 10km² | 더 작은 영역으로 요청 |
| 레이어 없음 | 레이어 ID 오타/대소문자 | CSV 파일에서 확인 |
