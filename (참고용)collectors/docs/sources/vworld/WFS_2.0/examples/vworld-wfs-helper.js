/**
 * V-world WFS 2.0 API 헬퍼 함수
 * 
 * 사용법:
 *   const wfs = new VWorldWFS('YOUR_API_KEY', 'http://localhost');
 *   wfs.getFeatures('LT_C_LANDINFOBASEMAP', bbox).then(data => {...});
 */

class VWorldWFS {
    constructor(apiKey, domain = 'http://localhost') {
        this.apiKey = apiKey;
        this.domain = domain;
        this.baseUrl = 'https://api.vworld.kr/req/data?';
    }

    /**
     * Data API로 GetFeature 요청
     * 
     * @param {string} layerId - 레이어 ID (대문자, 예: 'LT_C_LANDINFOBASEMAP')
     * @param {string|Array} geomfilter - 공간 필터 (BOX 문자열 또는 [minX,minY,maxX,maxY] 배열)
     * @param {Object} options - 추가 옵션
     * @returns {Promise} 응답 데이터
     */
    async getFeatures(layerId, geomfilter, options = {}) {
        const {
            size = 100,
            page = 1,
            geometry = true,
            attribute = true,
            crs = 'EPSG:3857'
        } = options;

        // geomfilter를 BOX 문자열로 변환
        let geomfilterStr;
        if (Array.isArray(geomfilter)) {
            geomfilterStr = `BOX(${geomfilter.join(',')})`;
        } else {
            geomfilterStr = geomfilter;
        }

        const params = {
            key: this.apiKey,
            domain: this.domain,
            service: 'data',
            version: '2.0',
            request: 'GetFeature',
            format: 'json',
            size: size,
            page: page,
            geometry: geometry,
            attribute: attribute,
            crs: crs,
            data: layerId,
            geomfilter: geomfilterStr
        };

        const url = this.baseUrl + new URLSearchParams(params).toString();

        try {
            const response = await fetch(url);
            const data = await response.json();

            if (data.response.status === 'OK') {
                return {
                    success: true,
                    total: parseInt(data.response.record.total),
                    features: data.response.result.featureCollection.features,
                    page: data.response.page
                };
            } else {
                return {
                    success: false,
                    error: data.response.error
                };
            }
        } catch (error) {
            return {
                success: false,
                error: { text: error.message }
            };
        }
    }

    /**
     * WFS API로 GetFeature 요청 (JSONP 필요 시)
     * 
     * @param {string} layerId - 레이어 ID (소문자, 예: 'lt_c_landinfobasemap')
     * @param {string|Array} bbox - 경계 박스 (문자열 또는 [minX,minY,maxX,maxY] 배열)
     * @param {Object} options - 추가 옵션
     * @returns {Promise} 응답 데이터
     */
    async getFeaturesWFS(layerId, bbox, options = {}) {
        const {
            maxFeatures = 100,
            output = 'json',
            crs = 'EPSG:900913'
        } = options;

        // bbox를 문자열로 변환
        let bboxStr;
        if (Array.isArray(bbox)) {
            bboxStr = bbox.join(',');
        } else {
            bboxStr = bbox;
        }

        return new Promise((resolve, reject) => {
            const callbackName = 'wfsCallback' + Date.now() + Math.random().toString(36).substr(2, 9);
            
            window[callbackName] = function(data) {
                delete window[callbackName];
                
                if (data.ServiceExceptionReport) {
                    resolve({
                        success: false,
                        error: data.ServiceExceptionReport.ServiceException
                    });
                } else {
                    resolve({
                        success: true,
                        features: data.features || [],
                        type: data.type
                    });
                }
            };

            const params = {
                SERVICE: 'WFS',
                REQUEST: 'GetFeature',
                TYPENAME: layerId,
                BBOX: bboxStr,
                VERSION: '1.1.0',
                MAXFEATURES: maxFeatures,
                SRSNAME: crs,
                OUTPUT: output,
                KEY: this.apiKey,
                DOMAIN: this.domain,
                format_options: 'callback:' + callbackName
            };

            const script = document.createElement('script');
            script.src = 'https://api.vworld.kr/req/wfs?' + new URLSearchParams(params).toString();
            script.onerror = () => {
                delete window[callbackName];
                reject(new Error('WFS 요청 실패'));
            };
            document.head.appendChild(script);
        });
    }

    /**
     * 환경 변수에서 설정 로드 (브라우저 환경에서는 제한적)
     * 
     * @param {string} envPath - .env 파일 경로 (서버사이드만 가능)
     * @returns {Object} {apiKey, domain}
     */
    static loadFromEnv(envPath) {
        // Node.js 환경에서만 동작
        if (typeof require !== 'undefined') {
            const fs = require('fs');
            const envContent = fs.readFileSync(envPath, 'utf8');
            const lines = envContent.split('\n');
            
            let apiKey = '';
            let domain = 'http://localhost';
            
            lines.forEach(line => {
                const trimmed = line.trim();
                if (trimmed.startsWith('vworld_api_key=')) {
                    apiKey = trimmed.split('=')[1].trim();
                } else if (trimmed.startsWith('vworld_domain=')) {
                    domain = trimmed.split('=')[1].trim();
                }
            });
            
            return { apiKey, domain };
        }
        
        return { apiKey: '', domain: 'http://localhost' };
    }
}

// 사용 예제
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VWorldWFS;
}

// 브라우저 환경에서 전역으로 사용
if (typeof window !== 'undefined') {
    window.VWorldWFS = VWorldWFS;
}
