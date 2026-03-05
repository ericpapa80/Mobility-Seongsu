"""SBIZ 환경 변수 확인 스크립트."""

import os
from dotenv import load_dotenv

load_dotenv()

keys = ['SBIZ_SERVICE_KEY', 'DATA_GO_KR_SERVICE_KEY', 'PUBLICDATA_SERVICE_KEY', 'SERVICE_KEY']

print("Checking SBIZ environment variables:")
print("-" * 50)
for k in keys:
    value = os.getenv(k, "")
    status = "SET" if value else "NOT SET"
    if value:
        # 값의 일부만 표시 (보안)
        preview = value[:10] + "..." if len(value) > 10 else value
        print(f"{k}: {status} (value: {preview})")
    else:
        print(f"{k}: {status}")
