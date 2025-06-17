# 표준 라이브러리
from collections import defaultdict
from datetime import timedelta, date, datetime
import json
import typing

# core Django
from django.db.models import Exists, OuterRef, Prefetch
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

# django third party apps
from apscheduler.schedulers.background import BackgroundScheduler

# project apps
from .forms import PracticeApplyForm, ScheduleCreateForm, SongAddForm, SignupForm, LoginForm
from .models import Schedule, SongData, Apply, Session, WhyNotComing, Timetable, ArrivalTime
from .metrics import AttendanceStatistics
from .timetable import BaseOptimizer, ScheduleOptimizer, RouteOptimizer, timetable_df_to_objects, get_all_na_users
from banhyang.core.utils import weekday_dict, calculate_eta, date_to_integer, integer_to_date

# LOGIN Redirecting 페이지 -> 로그인이 필요한 페이지에 로그인 없이 접근할 경우 해당 링크로 redirect됨
URL_LOGIN = '/login'

# type alias when response is redirect or response
RedirectOrResponse = typing.Union[HttpResponse, HttpResponseRedirect]


sched = BackgroundScheduler()

# oracle free tier의 auto inactive 방지용
def prevent_db_sleep():
    print("Awake db connection")
    print(len(get_user_model().objects.all()))

sched.add_job(prevent_db_sleep, 'interval', days=6)


# 회원 가입 view
def signup(request:HttpRequest) -> RedirectOrResponse:
    context ={}
    context['is_signup'] = True
    if request.method == "POST":
        # form validation
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            authenticate(username=username, password=raw_password)
            messages.success(request, "회원가입 신청이 완료되었습니다. 임원진 승인 후 이용 가능합니다.")
            return redirect('practice_apply')
    else:
        form = SignupForm()

    context['form'] = form
    return render(request, 'login.html',context)

def login(request:HttpRequest):
    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=raw_password)
            if user is not None:
                auth_login(request, user)
                return redirect('practice_apply')
    return render(request, 'login.html', {'form':form})

@login_required(login_url=URL_LOGIN)
def practice_apply(request:HttpRequest) -> HttpResponse:
    """
    합주 불참 신청 페이지
    """
    context = {}
    # is_current(불참을 받을 합주)가 체크된 합주 일정을 가져옴
    current_practice = Schedule.objects.filter(is_current=True).order_by('date')
    if len(current_practice):
        form = PracticeApplyForm()
    else:
        form = None
    # SUBMIT 했을 시
    if request.method == "POST":
        form = PracticeApplyForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "제출되었습니다.")
            form = PracticeApplyForm()
        else:
            # Validation 에러 발생
            messages.error(request, form.non_field_errors()[0])
            form = PracticeApplyForm(request.POST)

    context['form'] = form
    return render(request, 'practice_apply.html', context=context)


def attendance_check_index(request:HttpRequest) -> HttpResponse:
    """
    출석체크 여부 확인을 위한 합주 목록
    """
    context = {}

    timetable_objects = Timetable.objects.distinct().values('schedule_id')
    id_list = [x['schedule_id'] for x in timetable_objects]
    temp_date_list = [x.date for x in Schedule.objects.filter(id__in=id_list)]
    date_list = list(set(temp_date_list))
    date_list.sort(reverse=True)

    date_int_list = [(x.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(x.weekday()), date_to_integer(x)) for x in date_list]
    context['res'] = date_int_list
    return render(request, 'attendance_check_index.html', context=context)


def get_attendance_check(request:HttpRequest, date:int) -> HttpResponse:
    """
    선택한 날짜의 출석체크 여부 확인 페이지
    """
    context = {}
    date = integer_to_date(date)
    user_objects = get_user_model().objects.all()
    # eta/real arrival time 비교 dict -> {날짜 : {사람 : [ETA, 실제 도착 시간, 지각(분)]}}
    attendance_dict = {}
    date_to_string = date.strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(date.weekday())
    attendance_dict[date_to_string] = {}

    # 각 인원 별 도착시간과 ETA를 비교하여 출석/지각/불참 여부 계산
    for user_object in user_objects:
        arrival_time_object = ArrivalTime.objects.filter(user_id=user_object, date=date)
        eta = calculate_eta(user_object=user_object, date=date)
        late_time = None
        if arrival_time_object:
            arrival_time = arrival_time_object[0].arrival_time
        else:
            arrival_time = None
        if arrival_time and eta:
            delta = (datetime.combine(datetime.today(), arrival_time) - datetime.combine(datetime.today(), eta)).total_seconds()
            late_time = max(int(delta / 60), 0)
        attendance_dict[date_to_string][user_object.name] = [eta, arrival_time, late_time]

    context['res'] = attendance_dict
    return render(request, 'get_attendance.html', context=context)


@staff_member_required
def setting(request:HttpRequest) -> HttpResponse:
    """
    불참 조사 받을 합주 날짜 선택 및 불참 조사 미제출 인원 확인 페이지
    """
    context = {}

    # 불참 받을 합주 날짜 선택 후 제출 혹은 곡 당 minute, room number 수정
    if request.method == "POST":
        res = dict(request.POST)
        schedule_objects = Schedule.objects.all()

        # 모든 합주 일정의 is current false 후 선택한 일정만 true로 변경
        schedule_objects.update(is_current=False)
        if 'schedule_checkbox' in res:
            Schedule.objects.filter(id__in=res['schedule_checkbox']).update(is_current=True)
        for schedule_object in schedule_objects:
            idx = schedule_object.id
            Schedule.objects.filter(id=idx).update(min_per_song=int(res['minute_' + str(idx)][0]), rooms=int(res['rooms_' + str(idx)][0]))
        messages.success(request, "변경되었습니다.")

    # 미제출 인원 목록 조회
    schedules = Schedule.objects.all().order_by('date')

    current_schedule_objects = Schedule.objects.filter(is_current=True).order_by('date')
    temp_not_submitted_list = []
    for current_schedule_object in current_schedule_objects:
        not_submitted = get_user_model().objects.filter(~Exists(Apply.objects.filter(user_id=OuterRef('pk'), schedule_id=current_schedule_object)), is_confirmed=True, is_superuser=False)
        temp_not_submitted_list.extend([i.name for i in not_submitted])

    not_submitted_list = list(set(temp_not_submitted_list))
    not_submitted_list.sort()

    context['schedules'] = schedules
    context['not_submitted'] = not_submitted_list

    return render(request, 'setting.html', context=context)


@staff_member_required
def schedule_create(request:HttpRequest) -> RedirectOrResponse:
    """
    합주 일정 생성 페이지
    """
    context = {}
    form = ScheduleCreateForm()
    if request.method == "POST":
        form = ScheduleCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('setting')
        else:
            # validation fail
            messages.error(request, form.non_field_errors()[0])
            form = ScheduleCreateForm(request.POST)

    context['form'] = form
    return render(request, 'schedule_create.html', context=context)


@staff_member_required
def schedule_delete(_:HttpRequest, schedule_id:int) -> HttpResponseRedirect:
    """
    합주 일정 목록에서 특정 날짜 삭제 시 해당 합주 일정의 id를 url parameter로 받아와 삭제
    """
    practice_to_delete = get_object_or_404(Schedule, id=schedule_id)
    practice_to_delete.delete()
    return redirect('setting')


@staff_member_required
def song_list(request:HttpRequest) -> HttpResponse:
    """
    곡 목록 CRUD 페이지
    """
    context = {}
    form = SongAddForm()
    # 곡 추가하는 경우
    if request.method == "POST" and 'add' in request.POST:
        form = SongAddForm(request.POST)
        # forms에서 validation 진행
        if form.is_valid():
            form.save()
            form = SongAddForm()
            messages.success(request, "등록되었습니다.")
        else:
            # validation error
            messages.error(request, form.non_field_errors()[0])
            form = SongAddForm(request.POST)

    # 곡 삭제하는 경우
    if request.method == "POST" and 'delete' in request.POST:
        # 체크된 곡들 삭제하기
        delete_ids = request.POST.getlist('song_id')
        if delete_ids:
            d = SongData.objects.filter(id__in=delete_ids)
            try:
                d.delete()
                messages.success(request, "삭제되었습니다.")
            except:
                messages.error(request, "삭제에 실패하였습니다. 다시 시도해주세요.")
        else:
            messages.error(request, "하나 이상의 곡을 선택해주세요.")

    # 곡의 합주 우선순위 업데이트
    if request.method == "POST" and 'updateId' in request.POST and request.POST['updateId']:
        res = dict(request.POST)
        update_Id = res['updateId'][0]
        update_value = res[update_Id][0]
        u = SongData.objects.filter(id=update_Id).update(priority=update_value)

    # 곡 목록 보여주기
    session_qs = Session.objects.select_related('user_id')
    songs = SongData.objects.prefetch_related(Prefetch('session', queryset=session_qs)).order_by('songname')
    song_dict = {}
    for song in songs:
        session_dict = defaultdict(list)
        sessions = song.session.all()
        for s in sessions:
            session_dict[s.instrument].append(s.user_id.name)
        session_dict = {key: ", ".join(val) for key, val in session_dict.items()}
        # 각 곡별 세션 데이터를 딕셔너리로 정리
        song_dict[song] = dict(session_dict)
    context['songs'] = song_dict
    context['form'] = form
    return render(request, 'song_list.html', context=context)


@staff_member_required
def user_confirm_list(request:HttpRequest) -> HttpResponse:
    context : dict = {}
    User_model = get_user_model()

    # 가입 대기 목록
    not_confirmed_users = User_model.objects.filter(is_confirmed=False).order_by('name')
    # 가입 완료 목록
    confirmed_users = User_model.objects.filter(is_confirmed=True, is_superuser=False).order_by('name')

    context['not_confirmed'] = not_confirmed_users
    context['confirmed'] = confirmed_users

    # 가입 승인하는 경우
    if request.method == "POST" and 'confirmed' in request.POST:
        confirm_ids = request.POST.getlist('user_id')
        if confirm_ids:
            c = User_model.objects.filter(id__in=confirm_ids)
            for obj in c:
                obj.is_confirmed = True
            update_counts = User_model.objects.bulk_update(c, ['is_confirmed'])
            messages.info(request, "가입 승인이 완료되었습니다.")
        else:
            messages.info(request, "한명 이상의 인원을 선택해주세요.")


    # 기존 인원을 삭제하는 경우
    if request.method == "POST" and ("delete" in request.POST or "deny" in request.POST):
        delete_ids = request.POST.getlist('user_id')
        if delete_ids:
            d = User_model.objects.filter(id__in=delete_ids)
            if request.user in d:
                messages.error(request, "본인의 계정은 삭제할 수 없습니다. 다시 시도해주세요.")
            else:
                d.delete()
                messages.info(request, "삭제가 완료되었습니다.")
        else:
            messages.info(request, "한명 이상의 인원을 선택해주세요.")

    return render(request, 'user_confirm_list.html', context=context)

@staff_member_required
def grant_admin(_:HttpRequest, user_id:int) -> HttpResponseRedirect:
    User_model = get_user_model()
    try:
        user = User_model.objects.get(id=user_id)
        user.is_staff = True
        user.save()
        messages.success(_, user.username + "님에게 운영자 권한이 부여되었습니다.")
    except User_model.DoesNotExist:
        messages.error(_, "유저를 찾을 수 없습니다.")
    return redirect("user_confirm_list")

@staff_member_required
def timetable(request:HttpRequest) -> HttpResponse:
    """
    !! 합주 시간표 생성 페이지 !!
    
    자세한 로직은 timetable.py 참고하기
    """
    context = {}

    schedule_opt = ScheduleOptimizer()
    schedule_opt.retreive_data()
    schedule_opt.process()
    schedule_opt.optimize()
    schedule_df_dict, na_indexes = schedule_opt.post_process()

    # 웹의 가독성을 위해 dataframe의 Nan을 'X'로 변경
    schedule_df_dict = {i: v.fillna("X") for i, v in schedule_df_dict.items()}
    # 동선 최적화 위한 데이터 가져오기
    for i,df in schedule_df_dict.items():
        route_opt = RouteOptimizer(df)
        route_opt.retreive_data()
        route_opt.process()
        route_opt.optimize()
        new_dataframe = route_opt.post_process()

        schedule_df_dict[i] = new_dataframe

    # 웹 가독성을 위해 시간표들의 dictionary의 키를 schedule id -> MM월 DD일 (요일)으로 변환
    schedule_df_result = {}
    for i, v in schedule_df_dict.items():
        schedule_df_result[schedule_opt.practiceId_to_date[i]] = [i,v]
        na_indexes[i].append(schedule_opt.practiceId_to_date[i])

    context['df'] = schedule_df_result

    # 합주 진행하지 않는 (곡 목록의 우선 순위 상에서 합주 X로 선택된) 곡들
    na_songs = SongData.objects.filter(priority=-1)
    na_songs = [x.songname for x in na_songs]
    context['na_songs'] = na_songs

    na_users = get_all_na_users(schedule_opt.available_dict, 
                                schedule_opt.song_session_set, 
                                schedule_opt.songId_to_name)
    context['na_users'] = na_users
    context['na_indexes'] = na_indexes

    # 불참 여부 미제출 인원 체크하기
    schedule_objects = schedule_opt.schedule_objects
    for schedule_object in schedule_objects:
        not_submitted = get_user_model().objects.filter(~Exists(Apply.objects.filter(user_id=OuterRef('pk'), schedule_id=schedule_object)), is_confirmed=True, is_superuser=False)
        if not_submitted:
            messages.warning(request, "아직 불참 여부를 제출하지 않은 인원이 존재합니다!")

    # 시간표를 확정하는 경우
    if request.method == "POST":
        # POST 데이터 파싱하기 -> 기존 Dataframe의 순서 수정
        for key, value in request.POST.items():
            post_parsed = key.split('_')
            if post_parsed[0] == 'timetable':
                song_name = value
                parsed_id = int(post_parsed[1])
                col = int(post_parsed[2])
                row = int(post_parsed[3])
                schedule_df_dict[parsed_id].iloc[col, row] = song_name

        # 확정된 시간표를 db 저장하기 위해 데이터 가공
        timetable_object_dict = timetable_df_to_objects(schedule_df_dict, 
                                                        schedule_opt.practice_info, 
                                                        schedule_opt.song_objects)

        for schedule_id, v in timetable_object_dict.items():
            schedule_id = Schedule.objects.get(id=schedule_id)
            existing_timetable_object = Timetable.objects.filter(schedule_id=schedule_id)
            # DB에 존재하는 해당 합주 시간표 조회 후 삭제
            if existing_timetable_object:
                existing_timetable_object.delete()

            # Bulk 저장
            timetable_object_list = [Timetable(schedule_id=schedule_id, song_id=SongData.objects.get(id=song_id), start_time=info_tuple[0], end_time=info_tuple[1], room_name=info_tuple[2]) for song_id, info_tuple in v.items()]
            Timetable.objects.bulk_create(timetable_object_list)
            messages.success(request, "저장되었습니다.")

    return render(request, 'timetable.html', context=context)


@staff_member_required
def who_is_not_coming(request:HttpRequest) -> HttpResponse:
    """
    인원 별 불참 사유와 시간 확인 조회 페이지
    """
    context = {}
    apply_qs = Apply.objects.select_related('user_id')
    current_schedule = Schedule.objects.filter(is_current=True).prefetch_related(Prefetch('apply', queryset=apply_qs))
    schedule_info = {}
    when_and_why = {}

    if current_schedule:
        reason_why = {}
        not_available = {}
        for schedule in current_schedule:
            schedule_info[schedule.id] = {
                'id': schedule.id,
                'date': schedule.date.strftime("%y/%m/%d"),
                'starttime': schedule.starttime,
                'endtime': schedule.endtime
            }

            na = schedule.apply.all()
            schedule_id = schedule.id
            not_available[schedule_id] = defaultdict(list)

            # 불참 시간 정리(가공 전)
            for i in na:
                name = i.user_id.name
                time = i.not_available
                not_available[schedule_id][name].append(time)
            schedule_start_time = datetime.combine(date.today(), schedule.starttime)

            # 날짜 별 불참 시간 dictionary
            for name, not_available_list in not_available[schedule_id].items():
                not_available_list.sort()
                postprocessed_list = []
                j = None
                while not_available_list:
                    i = not_available_list.pop(0)
                    if i == -1:
                        postprocessed_list = ["전참"]
                        break
                    if j is None:
                        start_time = schedule_start_time + timedelta(minutes=10 * i)
                        end_time = start_time + timedelta(minutes=10)
                    elif i == j + 1:
                        end_time += timedelta(minutes=10)
                        if not not_available_list:
                            postprocessed_list.append(start_time.strftime("%H:%M") + "~" + end_time.strftime("%H:%M"))
                    else:
                        postprocessed_list.append(start_time.strftime("%H:%M") + "~" + end_time.strftime("%H:%M"))
                        start_time = schedule_start_time + timedelta(minutes=10 * i)
                        end_time = start_time + timedelta(minutes=10)

                    j = i
                not_available[schedule_id][name] = ', '.join(postprocessed_list)

            # 날짜 별 불참 사유 dictionary
            reason_why[schedule_id] = {}
            reason_object = WhyNotComing.objects.filter(schedule_id=schedule).select_related('user_id')
            for i in reason_object:
                reason_why[schedule_id][i.user_id.name] = i.reason

            # 웹에 표시 위한 최종 정제 -> 불참시간(사유) 형식
            date_to_string = schedule.date.strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(schedule.date.weekday())
            when_and_why[date_to_string] = {}
            for name, t in not_available[schedule_id].items():
                if name in reason_why[schedule_id]:
                    concatenated = t + " (" + reason_why[schedule_id][name] + ")"
                else:
                    concatenated = t

                when_and_why[date_to_string][name] = concatenated
            sorted_dict = sorted(when_and_why[date_to_string].items(), key=lambda item: item[1])
            when_and_why[date_to_string] = sorted_dict
    else:
        when_and_why = None

    context['when_and_why'] = when_and_why

    return render(request, 'who_is_not_coming.html', context=context)


@staff_member_required
def metrics(request:HttpRequest) -> HttpResponse:
    """
    합주 관련 통계 페이지

    자세한 통계 데이터는 metrics.py 확인
    """
    context = {}

    stats = AttendanceStatistics()
    user_percentage, schedule_percentage, song_percentage, total_percentage = stats.get_metrics()
    
    # 합주 id를 날짜로 변경하고 정렬 후 라벨과 데이터로 나눔
    id_to_date_dict = {}
    for schedule_id, percentage in schedule_percentage.items():
        schedule_object = Schedule.objects.get(id=schedule_id)
        schedule_date = schedule_object.date
        id_to_date_dict[schedule_date] = percentage
    
    schedule_label = sorted(id_to_date_dict.keys())
    schedule_data = [id_to_date_dict[x] for x in schedule_label]
    schedule_label = [x.strftime('%m.%d') for x in schedule_label]

    # 곡 object를 제목으로 변경하고 참석률 순으로 정렬 후 라벨과 데이터로 나눔
    sorted_song_percentage = {k.songname : v for k, v in sorted(song_percentage.items(), key=lambda x:x[1])}
    song_label = json.dumps(list(sorted_song_percentage.keys()))
    song_data = list(sorted_song_percentage.values())

    # 유저별 참석률을 정렬 후 라벨과 데이터로 나눔
    sorted_user_percentage = {k : v for k, v in sorted(user_percentage.items(), key= lambda x: x[1])}
    user_label = json.dumps(list(sorted_user_percentage.keys()))
    user_data = list(sorted_user_percentage.values())


    context['daily_label'] = json.dumps(schedule_label)
    context['daily_data'] = schedule_data

    context['song_label'] = song_label
    context['song_data'] = song_data

    context['user_label'] = user_label
    context['user_data'] = user_data

    context['total_chart'] = total_percentage

    return render(request, 'metrics.html', context=context)
