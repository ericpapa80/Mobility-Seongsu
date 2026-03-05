# V-world WFS 2.0 예제 파일

이 폴더에는 V-world WFS 2.0 API 사용 예제가 포함되어 있습니다.

## 파일 목록

### 1. `wfs-example.html`
- **WFS API** (`req/wfs`) 사용 예제
- 브라우저에서 직접 실행 가능
- JSONP를 사용한 요청 처리

### 2. `data-api-example.html` ⭐ 권장
- **Data API** (`req/data`) 사용 예제
- WFS보다 간단하고 일관된 JSON 응답
- 브라우저에서 직접 실행 가능

### 3. `vworld-wfs-helper.js`
- 재사용 가능한 헬퍼 클래스
- `VWorldWFS` 클래스로 API 호출 간소화
- 브라우저 및 Node.js 환경 모두 지원

## 빠른 시작

### 1. 환경 설정

`.env` 파일 생성 (프로젝트 루트):

```env
vworld_api_key=YOUR_API_KEY
vworld_domain=http://localhost
```

### 2. 예제 실행

#### 브라우저에서 실행

1. `data-api-example.html` 또는 `wfs-example.html` 열기
2. 인증키와 도메인 입력
3. 레이어 선택 및 BBOX 설정
4. "요청 실행" 버튼 클릭

#### JavaScript에서 사용

```html
<script src="vworld-wfs-helper.js"></script>
<script>
    const wfs = new VWorldWFS('YOUR_API_KEY', 'http://localhost');
    
    // Data API 사용 (권장)
    wfs.getFeatures('LT_C_LANDINFOBASEMAP', [14134500, 4518600, 14136500, 4520600])
        .then(result => {
            if (result.success) {
                console.log('총 건수:', result.total);
                console.log('피처:', result.features);
            } else {
                console.error('오류:', result.error);
            }
        });
</script>
```

#### Node.js에서 사용

```javascript
const VWorldWFS = require('./vworld-wfs-helper.js');

// .env에서 로드
const { apiKey, domain } = VWorldWFS.loadFromEnv('.env');
const wfs = new VWorldWFS(apiKey, domain);

// 요청
wfs.getFeatures('LT_C_LANDINFOBASEMAP', [14134500, 4518600, 14136500, 4520600])
    .then(result => {
        if (result.success) {
            console.log('총 건수:', result.total);
        }
    });
```

## 주요 레이어 예시

- `LT_C_LANDINFOBASEMAP` - LX맵
- `LT_C_SPBD` - 도로명주소건물
- `LP_PA_CBND_BUBUN` - 지적도 부번
- `LT_C_UQ111` - 도시지역

더 많은 레이어는 `../브이월드_WFS_컬럼정보.csv` 참고

## 주의사항

1. **인증키와 도메인**: vworld 개발자센터에 등록된 값과 정확히 일치해야 함
2. **geomFilter 제한**: BOX 면적은 10km² 이내
3. **레이어 ID 대소문자**: 
   - WFS: 소문자 (`lt_c_landinfobasemap`)
   - Data API: 대문자 (`LT_C_LANDINFOBASEMAP`)

## 문제 해결

- **INCORRECT_KEY**: KEY·DOMAIN 확인
- **INVALID_RANGE**: geomFilter 면적을 10km² 이하로 축소
- **레이어 없음**: 레이어 ID 대소문자 확인
