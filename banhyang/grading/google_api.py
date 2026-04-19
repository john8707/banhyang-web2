import io
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request

from .models import GoogleOAuthToken
# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email"
    ]

def get_google_credentials(user_email):
    """DB에 저장된 특정 유저의 토큰을 읽어 유효한 creds 객체를 반환합니다."""
    try:
        token_obj = GoogleOAuthToken.objects.get(email=user_email)
    except GoogleOAuthToken.DoesNotExist:
        raise Exception("DB에 저장된 토큰이 없습니다. 다시 로그인해주세요.")
        
    token_data = json.loads(token_obj.token_json)
    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_obj.token_json = creds.to_json()
            token_obj.save()
        else:
            raise Exception("토큰이 만료되었습니다. 다시 로그인해주세요.")
            
    return creds

def get_local_service(drive_cat: str, user_email: str):
    """이메일을 넘겨받아 해당 유저의 권한으로 API 서비스 객체를 빌드합니다."""
    creds = get_google_credentials(user_email)
    
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
