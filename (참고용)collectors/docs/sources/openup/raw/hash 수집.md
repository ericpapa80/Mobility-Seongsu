cURL(bash)

curl 'https://api.openub.com/v2/pro/bd/hash' \
  -H 'accept: */*' \
  -H 'accept-language: ko-KR,ko;q=0.9' \
  -H 'access-token: 367d99d0-6ffb-45af-9d2e-0efdea4dcea5' \
  -H 'content-type: application/json' \
  -H 'origin: https://pro.openub.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://pro.openub.com/' \
  -H 'sec-ch-ua: "Chromium";v="143", "Not A(Brand";v="24"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-site' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36' \
  --data-raw '{"cellTokens":["357ca181","357ca18f","357ca1ed"]}'

======

Request Header

:authority
api.openub.com
:method
POST
:path
/v2/pro/bd/hash
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
ko-KR,ko;q=0.9
access-token
367d99d0-6ffb-45af-9d2e-0efdea4dcea5
content-length
49
content-type
application/json
origin
https://pro.openub.com
priority
u=1, i
referer
https://pro.openub.com/
sec-ch-ua
"Chromium";v="143", "Not A(Brand";v="24"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"Windows"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-site
user-agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36

======

request payload

{"cellTokens":["357ca181","357ca18f","357ca1ed"]}

======

preview

{
  "bd": {
    "NqIHLbnXt-ubNp": {
      "ROAD_ADDR": "서울특별시 서초구 반포대로 333",
      "ADDR": "서울특별시 서초구 반포동 1",
      "bd_nms": [
        "래미안 원베일리"
      ],
      "decodedRdnu": "11650107212100300033300000",
      "markerPoint": [
        126.998105,
        37.5068737
      ],
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          "a~bpfA_ekfqFhObs@seEfiCcgAq`Drl@{^sIsVjd@kQlj@cS`l@cSb~@m\\`b@poBsCdA"
        ]
      },
      "center": [
        126.998105,
        37.5068737
      ]
    },
    "NqIHLbnZ4-Hwvh": {
      "ROAD_ADDR": "서울특별시 서초구 올림픽대로 2085-18",
      "ADDR": "서울특별시 서초구 반포동 115-1",
      "bd_nms": [
        "서래나루 한강수상택시 도선장"
      ],
      "decodedRdnu": "11650107212100400208500018",
      "markerPoint": [
        126.9931147,
        37.5097979
      ],
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          "qelpfA__`fqFuFsF_F_JrB}DlByArGzG~DvHmBvDqB~A"
        ]
      },
      "center": [
        126.9931147,
        37.5097979
      ]
    },
    "NqIHLbnZ4-Hwvd": {
      "ROAD_ADDR": "서울특별시 서초구 올림픽대로 2085-14",
      "ADDR": "서울특별시 서초구 반포동 650",
      "bd_nms": [],
      "decodedRdnu": "11650107212100400208500014",
      "markerPoint": [
        126.9953757,
        37.51204
      ],
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          "ucrpfA}rcfqFwDeP_Fc`@vBs^jFgTvNyS`Ju@tIhCdJlDnIvKrKzI`FzG~SxUhIzQjAvPIfWuFvPoOhGmPnEmPd@uRWuVuOeGqO"
        ]
      },
      "center": [
        126.9953757,
        37.51204
      ]
    },
    "Mm1KW94VNXjBe_": {
      "ROAD_ADDR": "서울특별시 용산구 올림픽대로 2085-96",
      "ADDR": "서울특별시 용산구 용산동6가 451",
      "bd_nms": [
        "더리버"
      ],
      "decodedRdnu": "11170135212100400208500096",
      "markerPoint": [
        126.9845532,
        37.5081164
      ],
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          "w{jpfAmfmeqFpPanEniB|xAaKzcC_oBwN"
        ]
      },
      "center": [
        126.9845532,
        37.5081164
      ]
    },
    "NhWc1wT78BZW98": {
      "ROAD_ADDR": "서울특별시 동작구 현충로 151",
      "ADDR": "서울특별시 동작구 흑석동 28",
      "bd_nms": [
        "한강현대아파트"
      ],
      "decodedRdnu": "11590105311900900015100000",
      "markerPoint": [
        126.9703478,
        37.5066525
      ],
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          "sjepfAslxdqFjDiC~O`P_@fAx@hAYvQPxm@WrXoH{CwKla@fPnIoHj]aXbdAyEvOwCoC}Aw@cF}FgKqG_@z@yLaEoAfCoc@qe@vFc@~B{GfIwMlCeGfMiTbHsNp^swA~Le\\~E_LtA{A"
        ]
      },
      "center": [
        126.9703478,
        37.5066525
      ]
    }
  },
  "keys": [
    "357ca181",
    "357ca18f",
    "357ca1ed"
  ],
  "cacheHit": 0,
  "failedKeys": []
}