import re

# 토큰 파일 읽기
with open('docs/sources/openup/raw/260113_token', 'r', encoding='utf-8') as f:
    content = f.read()

# access-token 추출
token_match = re.search(r'OPENUP_ACCESS_TOKEN\s*=\s*([a-f0-9\-]+)', content)
access_token = token_match.group(1) if token_match else None

# cell_tokens 추출 (따옴표로 감싸진 문자열)
cell_tokens = re.findall(r'"([a-f0-9]+)"', content)
unique_tokens = sorted(set(cell_tokens))

# Python 리스트 형식으로 출력
print("# 새로운 access-token")
print(f'NEW_ACCESS_TOKEN = "{access_token}"')
print()
print("# 서울시 전체 및 경기도 일부 cellTokens")
print("SEOUL_GYEONGGI_CELL_TOKENS = [")
for i, token in enumerate(unique_tokens):
    if i == len(unique_tokens) - 1:
        print(f'    "{token}"')
    else:
        print(f'    "{token}",')
print("]")
