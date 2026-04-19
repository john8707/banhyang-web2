import io
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from .models import GoogleOAuthToken
# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_google_credentials():
    """DB에 저장된 토큰을 읽어 유효한 creds 객체를 반환하고, 필요시 갱신합니다."""
    
    # 1. DB에서 첫 번째(유일한) 토큰 레코드를 가져옵니다.
    token_obj = GoogleOAuthToken.objects.first()
    
    if not token_obj or not token_obj.token_json:
        raise Exception("DB에 저장된 토큰이 없습니다. /auth/login/ 으로 접속하여 인증해주세요.")
        
    # 2. JSON 문자열을 파싱하여 Credentials 객체 복원
    token_data = json.loads(token_obj.token_json)
    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
    # 3. 토큰 유효성 검사 및 갱신
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            # 토큰 갱신
            creds.refresh(Request())
            # ⭐️ 갱신된 새로운 토큰을 다시 DB에 업데이트
            token_obj.token_json = creds.to_json()
            token_obj.save()
        else:
            raise Exception("토큰이 만료되었고 갱신할 수 없습니다. 다시 로그인해주세요.")
            
    return creds

def get_local_service(drive_cat: str):
    """발급받은 creds를 이용해 API 서비스 객체를 빌드합니다."""
    creds = get_google_credentials()
    
    if drive_cat == "drive":
        return build('drive', 'v3', credentials=creds)
    elif drive_cat == "sheets":
        return build('sheets', 'v4', credentials=creds)

class GoogleService:
    def __init__(self, drive_service, sheets_service, folder_id: str):
        self.drive_service = drive_service
        self.sheets_service = sheets_service
        self.folder_id = folder_id

    def list_files_in_folder(self):
        service = self.drive_service
        try:
            # 특정 폴더 내의 파일 쿼리 (삭제되지 않은 파일만)
            query = f"'{self.folder_id}' in parents and trashed = false"
            results = service.files().list(
                q=query, 
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()
            items = results.get('files', [])

            if not items:
                print('폴더 내에 파일이 없습니다.')
                return []
            
            return items
        except HttpError as error:
            print(f'에러 발생: {error}')
            return []
    
    def download_file(self, file_id, file_name):
        service = self.drive_service
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"{file_name} 다운로드 중... {int(status.progress() * 100)}%")
        
        return fh.getvalue()
    
    def create_spreadhseet_in_folder(self, title) -> str:
        file_metadata = {
            "name" : title,
            "mimeType" : 'application/vnd.google-apps.spreadsheet',
            "parents" : [self.folder_id]
        }

        spreadsheet_file = self.drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        spreadsheet_id = spreadsheet_file.get('id')

        headers = [["파일 id", "파일명", "작성자", "점수", "요약", "채점 근거", "번역본"]]
        self.append_spreadsheet_row(spreadsheet_id, headers)

        return spreadsheet_id
    
    def append_spreadsheet_row(self, spreadsheet_id, values):
        body = {'values': values}
        self.sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="A1",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
