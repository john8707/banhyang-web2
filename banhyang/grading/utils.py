import re

def extract_folder_id(url_or_id):
    """
    구글 드라이브 URL에서 폴더 ID를 추출합니다. 
    만약 이미 ID 형태라면 그대로 반환합니다.
    """
    # 폴더 ID 패턴 (보통 25~35자의 알판뉴메릭 문자)
    pattern = r'folders/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url_or_id)
    
    if match:
        return match.group(1)
    
    # URL 형식이 아니면 입력값을 그대로 ID로 간주 (이미 ID를 입력했을 경우 대비)
    return url_or_id.strip()