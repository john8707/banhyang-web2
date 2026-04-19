import os
import json
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.urls import reverse
from google_auth_oauthlib.flow import Flow
from .models import GoogleOAuthToken
from .google_api import get_local_service, GoogleService
from .text_parser import DocumentParser
from .gemini_service import GeminiLLMService
from .grading_service import EssayGrader


SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_google_flow(request: HttpRequest, state=None):
    client_config = json.loads(settings.GOOGLE_CREDENTIALS_JSON)

    return Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=request.build_absolute_uri(reverse('google_callback'))
    )

def google_login(request: HttpRequest):
    """
    구글 로그인창 redirect view
    """
    flow = get_google_flow(request)
    authorization_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    request.session['state'] = state
    request.session['code_verifier'] = flow.code_verifier

    return redirect(authorization_url)

def google_callback(request: HttpRequest):
    """
    구글 콜백 및 토큰 DB 저장
    """
    state = request.session.get('state')
    code_verifier = request.session.get('code_verifier')

    flow = get_google_flow(request, state)

    authorization_response = request.build_absolute_uri()
    flow.fetch_token(authorization_response=authorization_response, code_verifier=code_verifier)

    creds = flow.credentials

    # ⭐️ 핵심: 파일(token.json) 대신 DB에 저장합니다.
    # 나만 쓰는 용도이므로 기존 토큰이 있으면 덮어쓰고(업데이트), 없으면 새로 만듭니다.
    token_obj, created = GoogleOAuthToken.objects.get_or_create(id=1) 
    token_obj.token_json = creds.to_json()
    token_obj.save()
    return HttpResponse("구글 인증이 완료되어 토큰 DB 저장 완료")

def grading_home(request):
    """프론트엔드 HTML 창을 띄워주는 뷰"""
    return render(request, 'home.html')

def stream_grading(request):
    """SSE를 통해 실시간으로 채점 진행 상황을 쏴주는 제너레이터 뷰"""
    
    def event_stream():
        try:
            # 1. 초기화 및 준비
            yield f"data: {json.dumps({'status': 'info', 'message': '서버 인증 및 서비스 초기화 중...'})}\n\n"
            drive_service = get_local_service("drive")
            sheets_service = get_local_service("sheets")
            
            FOLDER_ID = '1Qrn6ERqgcl0pvSko0-wt-4bGwWmtvjQS'
            google_service = GoogleService(drive_service, sheets_service, FOLDER_ID)
            parser = DocumentParser()
            llm_service = GeminiLLMService()
            grader = EssayGrader(llm_service, llm_service)

            # 2. 결과 시트 생성
            import datetime
            now_str = datetime.datetime.now().strftime("%m/%d %H:%M")
            yield f"data: {json.dumps({'status': 'info', 'message': '결과 스프레드시트 생성 중...'})}\n\n"
            sheet_id = google_service.create_spreadhseet_in_folder(f"채점 결과 리포트 ({now_str})")

            # 3. 파일 목록 가져오기
            files = google_service.list_files_in_folder()
            valid_files = [f for f in files if f['mimeType'] in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']]
            total_files = len(valid_files)

            if total_files == 0:
                yield f"data: {json.dumps({'status': 'error', 'message': '폴더에 채점할 파일이 없습니다.'})}\n\n"
                return

            # 4. 본격적인 실시간 채점 루프 시작
            for idx, file in enumerate(valid_files, 1):
                # 프론트엔드로 "N번째 파일 시작" 알림 쏘기
                yield f"data: {json.dumps({'status': 'progress', 'current': idx, 'total': total_files, 'filename': file['name']})}\n\n"

                try:
                    file_bytes = google_service.download_file(file['id'], file['name'])
                    extracted_text = parser.extract_text(file_bytes, file['mimeType'])
                    
                    if not extracted_text:
                        raise ValueError("텍스트 추출 실패")
                        
                    result = grader.process_essay(extracted_text)
                    
                    row_data = [[
                        file['id'],
                        file['name'],
                        result.get('author_name', 'Unknown'),
                        result.get('score', 0),
                        "\n".join(result.get('summary', [])),
                        result.get('reasoning', ''),
                        result.get('translation', '')
                    ]]
                    google_service.append_spreadsheet_row(sheet_id, row_data)
                    
                    # 1개 완료될 때마다 성공 결과 쏘기
                    yield f"data: {json.dumps({'status': 'success', 'filename': file['name'], 'score': result.get('score')})}\n\n"
                    
                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'filename': file['name'], 'message': str(e)})}\n\n"

            # 5. 모든 작업 완료 알림
            yield f"data: {json.dumps({'status': 'done', 'sheet_id': sheet_id})}\n\n"

        except Exception as e:
            # 치명적인 에러 발생 시 처리
            yield f"data: {json.dumps({'status': 'fatal', 'message': f'시스템 에러: {str(e)}'})}\n\n"

    # StreamingHttpResponse로 제너레이터를 감싸서 리턴
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
