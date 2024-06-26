import json
import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Schedule, PracticeUser, KakaoTalkId, ArrivalTime


def get_username_by_id(id):
    try:
        user_object = KakaoTalkId.objects.get(id=id)
        return user_object.user_name.username
    except KakaoTalkId.DoesNotExist:
        return False


def get_username_by_name(name):
    try:
        user_object = PracticeUser.objects.get(username=name)
        return user_object
    except PracticeUser.DoesNotExist:
        return False


def simpletext_response(message):
    response = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": message}}]
        }
    }
    return response


@csrf_exempt
def attendance_check_only_first(request):
    if request.method == "POST":
        payloads = json.loads(request.body)

        user_id = payloads['userRequest']['user']['id']

        user_name = get_username_by_id(user_id)
        if not user_name:
            return JsonResponse(simpletext_response("등록되지 않은 사용자다냥.\n먼저 유저 등록 메뉴를 누르거나 '등록'이라고 채팅을 보내 등록을 진행해달라냐옹."))
        try:
            user_exist = PracticeUser.objects.get(username=user_name)
        except PracticeUser.DoesNotExist:
            return JsonResponse(simpletext_response("해당 인원이 존재하지 않다냥. 오탈자를 다시 확인하거나 관리자에게 문의해달라냥."))

        # 오늘 날짜 date + 0시0분0초 -> datetime 형식으로
        arrived_day_datetime = datetime.datetime.combine(datetime.date.today(), datetime.time(9, 0, 0, 0))
        # 오늘 합주가 존재하는지 validate
        schedule_exist = Schedule.objects.filter(date=arrived_day_datetime)
        if not schedule_exist:
            return JsonResponse(simpletext_response("금일 예정된 합주가 없다냥. 날짜를 다시 확인하거나 관리자에게 문의해달라냥."))

        # 5분전부터 인증 가능
        if not schedule_exist.filter(starttime__lte=(datetime.datetime.now() + datetime.timedelta(minutes=5)).time()):
            return JsonResponse(simpletext_response("합주 시작 5분 전부터 출석 체크를 할 수 있다냥. 좀만 기다려달라냥~"))

        arrival_exist = ArrivalTime.objects.filter(date=datetime.date.today(), user_name=user_exist)
        if arrival_exist:
            return JsonResponse(simpletext_response("이미 출석 체크가 되어있다냥. 출석 체크는 하루에 한 번만 가능하다냥!\n출석 시간 : " + arrival_exist[0].arrival_time.strftime('%H:%M')))

        s = ArrivalTime(user_name=user_exist)
        s.save()

        return JsonResponse(simpletext_response("출석 체크 되었다냥~"))


@csrf_exempt
def register(request):
    if request.method == "POST":
        payloads = json.loads(request.body)
        request_name = payloads['action']['params']['이름']
        user_id = payloads['userRequest']['user']['id']
        registered_name = get_username_by_id(user_id)
        user_object = get_username_by_name(request_name)

        # Practice user DB에 없는 경우 (즉 관리자가 등록하지 않은 경우)
        if not user_object:
            return JsonResponse(simpletext_response("데이터베이스에 등록되지 않은 이름입니다.\n이름을 다시 확인하거나 관리자에게 문의하세요."))

        # 이미 DB에 저장된 이름과 입력한 이름이 같은 경우
        if registered_name and request_name == registered_name:
            return JsonResponse(simpletext_response("이미 등록되어있습니다 :)"))

        # TODO 업데이트 기능
        if registered_name and request_name != registered_name:
            return JsonResponse(simpletext_response("이미 이 계정에 다른 이름으로 등록되어있습니다.\n관리자에게 문의하세요."))

        if not registered_name:

            check_if_id_is_registered = KakaoTalkId.objects.filter(user_name=user_object)
            if check_if_id_is_registered:
                check_if_id_is_registered.update(id=user_id)
            else:
                s = KakaoTalkId(id=user_id, user_name=user_object)
                s.save()
            return JsonResponse(simpletext_response("등록되었다냥"))
