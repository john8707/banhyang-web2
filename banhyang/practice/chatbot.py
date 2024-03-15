from django.shortcuts import render, redirect, get_object_or_404
from .models import Schedule, SongData, PracticeUser, Apply, Session, WhyNotComing, Timetable, AttendanceCheck, KakaoTalkId
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import datetime


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
            "outputs":[{"simpleText":{"text": message}}
            ]
        }
    }
    return response

@csrf_exempt
def attendance(request):
    if request.method == "POST":
        payloads = json.loads(request.body)
        user_id = payloads['userRequest']['user']['id']

        user_name = get_username_by_id(user_id)

        if not user_name:
            return JsonResponse(simpletext_response("등록되지 않은 사용자입니다. \n먼저 유저 등록 메뉴를 누르거나 '등록'이라고 채팅을 보내 등록을 진행해주세요."))

        now = datetime.datetime.now()
        try:
            user_exist = PracticeUser.objects.get(username=user_name)
        except PracticeUser.DoesNotExist:
            return JsonResponse(simpletext_response("해당 인원이 존재하지 않습니다. 오탈자를 다시 확인하거나 관리자에게 문의하세요."))

        #오늘 날짜 date + 0시0분0초 -> datetime 형식으로
        arrived_day_datetime = datetime.datetime.combine(datetime.date.today(), datetime.time(0,0,0,0,datetime.timezone.utc))

        #오늘 합주가 존재하는지 validate
        schedule_exist = Schedule.objects.filter(date=arrived_day_datetime)
        if not schedule_exist:
            return JsonResponse(simpletext_response("금일 예정된 합주가 없습니다. 날짜를 다시 확인하거나 관리자에게 문의하세요."))

        #저장된 합주 시간표가 있는지 validate
        timetable_exist = Timetable.objects.filter(schedule_id__in=schedule_exist)
        if not timetable_exist:
            return JsonResponse(simpletext_response("데이터베이스에 저장된 시간표가 존재하지 않습니다. 관리자에게 문의하세요."))
        
        #현재 인증가능한 합주가 있는지
        song_now = timetable_exist.filter(start_time__lte = (now + datetime.timedelta(minutes=4)).time(), end_time__gt=(now + datetime.timedelta(minutes=4)).time())
        if not song_now:
            return JsonResponse(simpletext_response("현재 출석 체크 가능한 곡이 존재하지 않습니다. 합주 시작 4분전 ~ 종료 4분전까지 인증 가능합니다."))
        
        #현재 진행중인 곡이 내가 참여하는 곡인지
        do_i_play_list=[]
        for i in song_now:
            do_i_play = i.song_id.session.filter(user_name=user_exist)
            if do_i_play:
                do_i_play_list.append(i)
        
        if not do_i_play_list:
            return JsonResponse(simpletext_response("현재 출석 체크 가능한 곡 중 연주하는 곡이 없습니다. 합주 시작 4분전 ~ 종료 4분전까지 인증 가능합니다."))
        
        attendance_exist = AttendanceCheck.objects.filter(timetable_id__in=do_i_play_list, user_name=user_exist)
        if attendance_exist:
            return JsonResponse(simpletext_response("이미 인증이 완료되었습니다. 합주 시작 4분전 ~ 종료 4분전까지 인증 가능합니다."))
        
        timetable_objects = do_i_play_list
        user_object = user_exist

        attendance_object_list = [AttendanceCheck(user_name = user_object, timetable_id=x) for x in timetable_objects]
        AttendanceCheck.objects.bulk_create(attendance_object_list)
        message = '출석 확인 되었습니다.\n곡제목 : \n' + '\n'.join([x.song_id.songname for x in timetable_objects])
        
        return JsonResponse(simpletext_response(message))
    

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
        if registered_name and request_name==registered_name:
            return JsonResponse(simpletext_response("이미 등록되어있습니다 :)"))
        
        #TODO 업데이트 기능
        if registered_name and request_name!=registered_name:
            return JsonResponse(simpletext_response("이미 이 계정에 다른 이름으로 등록되어있습니다.\n관리자에게 문의하세요."))
        

        if not registered_name:

            check_if_id_is_registered = KakaoTalkId.objects.filter(user_name = user_object)
            if check_if_id_is_registered:
                check_if_id_is_registered.update(id=user_id)
            else:
                s = KakaoTalkId(id = user_id, user_name=user_object)
                s.save()
            return JsonResponse(simpletext_response("등록되었다냥"))
