import json
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import HttpRequest, StreamingHttpResponse
from django.urls import reverse
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from .models import GoogleOAuthToken
from .google_api import get_local_service, GoogleService
from .text_parser import DocumentParser
from .gemini_service import GeminiLLMService
from .grading_service import EssayGrader
from .utils import extract_folder_id


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email"
]
DEFAULT_CRITERIA = """
    - What are the main arguments in the readings? (직접 인용 및 해석 포함)
    - How can the arguments be applied? (개인적 경험 또는 사회 현상 연관성)
    - What questions or critiques come up for you? (비판적 시각)
    - 직접 인용(페이지 기재) 없으면 감점!
"""
DEFAULT_FOLDER_ID = '1Qrn6ERqgcl0pvSko0-wt-4bGwWmtvjQS'
DEFAULT_MODEL = "gemini-3.1-pro-preview"
DEAFULT_SCORE_RANGE = "100, 95, 90, 85 중 하나의 점수만 부여"
DEFAULT_SCORE_STRICTNESS = "보통 (객관적이고 균형잡힌 평가)"


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

    # 발급받은 토큰(JWT)을 해독하여 사용자 이메일 추출
    client_id = json.loads(settings.GOOGLE_CREDENTIALS_JSON)['web']['client_id']
    id_info = id_token.verify_oauth2_token(creds.id_token, requests.Request(), client_id)
    user_email = id_info['email']


    # 추출한 이메일을 기준으로 DB에 토큰 저장 (있으면 업데이트, 없으면 생성)
    try:
        token_obj = GoogleOAuthToken.objects.get(email=user_email)
        token_obj.token_json = creds.to_json()
        token_obj.save()

    except GoogleOAuthToken.DoesNotExist:
        GoogleOAuthToken.objects.create(
            email=user_email,
            token_json=creds.to_json()
        )
    
    # 장고 서버가 "현재 접속한 사람이 누구인지" 기억하도록 세션에 이메일 저장
    request.session['current_user_email'] = user_email
    
    return redirect('grading_home')

def google_logout(request: HttpRequest):
    """세션을 완전히 비우고 로그인 페이지로 리다이렉트합니다."""
    request.session.flush()  # 현재 접속한 사용자의 모든 세션 데이터를 깨끗하게 삭제
    return redirect('google_login')

def grading_home(request: HttpRequest):
    """프론트엔드 HTML 창을 띄워주는 뷰"""
    
    # 1. 세션에서 현재 접속 중인 사용자의 이메일 확인
    user_email = request.session.get('current_user_email')
    
    # 2. 이메일 정보가 없으면(로그인 안 했으면) 무조건 로그인 뷰로 튕겨냅니다.
    if not user_email:
        return redirect('google_login') # urls.py에 지정한 로그인 경로의 name
        
    # 3. 로그인된 사용자라면, HTML에 이메일 데이터를 담아서 화면을 띄워줍니다.
    context = {
        'user_email': user_email
    }
    return render(request, 'home.html', context)

def stream_grading(request: HttpRequest):
    """SSE를 통해 실시간으로 채점 진행 상황을 쏴주는 제너레이터 뷰"""
    
    def event_stream():
        try:
            # 1. 초기화 및 준비
            yield f"data: {json.dumps({'status': 'info', 'message': '서버 인증 및 서비스 초기화 중...'})}\n\n"
            # ⭐️ 세션에서 현재 접속 중인 사용자의 이메일 확인
            user_email = request.session.get('current_user_email')
            if not user_email:
                yield f"data: {json.dumps({'status': 'fatal', 'message': '로그인 정보가 없습니다. 구글 인증을 먼저 진행해주세요.'})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'info', 'message': f'{user_email} 계정으로 초기화 중...'})}\n\n"
            
            # 서비스 객체를 생성할 때 이메일을 넘겨줍니다.
            drive_service = get_local_service("drive", user_email)
            sheets_service = get_local_service("sheets", user_email)
            
            # ⭐️ 프론트엔드에서 보낸 URL 가져오기 (없으면 기본값 사용)
            raw_url = request.GET.get('folder_url', DEFAULT_FOLDER_ID)
            folder_id = extract_folder_id(raw_url)

            # ⭐️ 선택된 모델 이름 읽기 (안 보냈을 경우 기본값은 pro)
            selected_model = request.GET.get('model', DEFAULT_MODEL)

            # ⭐️ 사용자가 입력한 채점 기준 
            user_criteria = request.GET.get('criteria', DEFAULT_CRITERIA)
            score_range = request.GET.get('score_range', DEAFULT_SCORE_RANGE) # ⭐️ 추가
            strictness = request.GET.get('strictness', DEFAULT_SCORE_STRICTNESS) # ⭐️ 추가

            # 사용할 api 및 parser 주입받기
            google_service = GoogleService(drive_service, sheets_service, folder_id)
            parser = DocumentParser()
            llm_service = GeminiLLMService(model_name=selected_model)
            grader = EssayGrader(llm_service, llm_service)

            # 2. 기존 스프레드 시트 확인
            yield f"data: {json.dumps({'status': 'info', 'message': '기존 채점 기록 확인 중...'})}\n\n"
            existing_files = google_service.list_files_in_folder()
            target_sheet = next((f for f in existing_files if f['name'].startswith("채점 결과 리포트") and f['mimeType'] == 'application/vnd.google-apps.spreadsheet'), None)

            graded_file_ids = set()
            sheet_id = None

            # 채점 기록이 존재하는 경우
            if target_sheet:
                sheet_id = target_sheet['id']
                result = sheets_service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range="A2:A"
                ).execute()

                rows = result.get('values', [])
                graded_file_ids = {row[0] for row in rows if row}

                yield f"data: {json.dumps({'status': 'info', 'message': f'기존 기록 발견: {len(graded_file_ids)}개 파일 스킵 예정'})}\n\n"

            # 채점 기록이 없으면 새로 생성
            else:
                import datetime
                now_str = datetime.datetime.now().strftime("%m/%d %H:%M")
                sheet_id = google_service.create_spreadhseet_in_folder(f"채점 결과 리포트 ({now_str})")
                yield f"data: {json.dumps({'status': 'info', 'message': '결과 스프레드시트 생성'})}\n\n"

            # 3. 파일 목록 가져오기
            valid_files = [f for f in existing_files if f['mimeType'] in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']]
            total_files = len(valid_files)

            if total_files == 0:
                yield f"data: {json.dumps({'status': 'error', 'message': '폴더에 채점할 파일이 없습니다.'})}\n\n"
                return

            # 4. 본격적인 실시간 채점 루프 시작
            for idx, file in enumerate(valid_files, 1):
                # ⏩ 스킵 기능: 이미 채점된 파일인지 확인
                if file['id'] in graded_file_ids:
                    yield f"data: {json.dumps({'status': 'skip', 'current': idx, 'total': total_files, 'filename': file['name']})}\n\n"
                    continue

                # 프론트엔드로 "N번째 파일 시작" 알림 쏘기
                yield f"data: {json.dumps({'status': 'progress', 'current': idx, 'total': total_files, 'filename': file['name']})}\n\n"

                try:
                    file_bytes = google_service.download_file(file['id'], file['name'])
                    extracted_text = parser.extract_text(file_bytes, file['mimeType'])
                    
                    if not extracted_text:
                        raise ValueError("텍스트 추출 실패")
                        

                    # 요약
                    info_result = grader.extract_info_and_translate(file['name'], extracted_text)
                    yield f"data: {json.dumps({'status': 'info', 'message': '번역 완료, 채점 진행 중'})}\n\n"

                    # 채점
                    score_result = grader.evaluate_score(extracted_text, user_criteria, score_range, strictness)
                    yield f"data: {json.dumps({'status': 'info', 'message': '채점 완료'})}\n\n"

                    # 결과 합치기
                    row_data = [[
                        file['id'],
                        file['name'],
                        info_result.get('author_name', 'Unknown'),
                        score_result.get('score', 0),
                        "\n".join(info_result.get('summary', [])),
                        score_result.get('reasoning', ''),
                        info_result.get('translation', '')
                    ]]
                    google_service.append_spreadsheet_row(sheet_id, row_data)
                    
                    # 1개 완료될 때마다 성공 결과 쏘기
                    yield f"data: {json.dumps({'status': 'success', 'filename': file['name'], 'score': score_result.get('score')})}\n\n"
                
                except (GeneratorExit, BrokenPipeError, ConnectionResetError):
                    print("🛑 프론트엔드에서 중지 버튼을 누르거나 창을 닫았습니다. 서버 작업을 즉시 중단합니다.")
                    break

                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'filename': file['name'], 'message': str(e)})}\n\n"

            # 5. 모든 작업 완료 알림
            yield f"data: {json.dumps({'status': 'done', 'sheet_id': sheet_id})}\n\n"

        except Exception as e:
            # 치명적인 에러 발생 시 처리
            yield f"data: {json.dumps({'status': 'fatal', 'message': f'시스템 에러: {str(e)}'})}\n\n"

    # StreamingHttpResponse로 제너레이터를 감싸서 리턴
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
