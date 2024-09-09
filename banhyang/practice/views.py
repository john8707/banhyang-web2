# 표준 라이브러리
from collections import defaultdict
from datetime import timedelta, date, datetime
import json

# core Django
from django.db.models import Exists, OuterRef
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

# django third party apps
from apscheduler.schedulers.background import BackgroundScheduler

# project apps
from .forms import PracticeApplyForm, ScheduleCreateForm, SongAddForm, UserAddForm
from .models import Schedule, SongData, PracticeUser, Apply, Session, WhyNotComing, Timetable, ArrivalTime
from .schedule import ScheduleRetriever, ScheduleProcessor, ScheduleOptimizer, SchedulePostProcessor, RouteRetriever, RouteProcessor, RouteOptimizer, RoutePostProcessor, BaseRetriever, timetable_df_to_objects
from .metrics import AttendanceStatistics
from banhyang.core.utils import weekday_dict, calculate_eta, date_to_integer, integer_to_date


URL_LOGIN = '/admin/login/?next=/practice/setting'


sched = BackgroundScheduler()

# oracle free tier의 auto inactive 방지용
def prevent_db_sleep():
    print("Awake db connection")
    len(PracticeUser.objects.all())

sched.add_job(prevent_db_sleep, 'interval', days=6)


def practice_apply(request):
    message = None
    context = {}
    current_practice = Schedule.objects.filter(is_current=True).order_by('date')
    if len(current_practice):
        form = PracticeApplyForm()
    else:
        form = None
    # SUBMIT 했을 시
    if request.method == "POST":
        form = PracticeApplyForm(request.POST)
        if form.is_valid():
            form.save()
            message = "제출되었습니다."
            form = PracticeApplyForm()
        else:
            message = form.non_field_errors()[0]
            form = PracticeApplyForm(request.POST)

    context['form'] = form
    context['message'] = message
    return render(request, 'practice_apply.html', context=context)


# 출석 체크 / 지각 여부 조회 위한 날짜 선택
def attendance_check_index(request):
    context = {}

    timetable_objects = Timetable.objects.distinct().values('schedule_id')
    id_list = [x['schedule_id'] for x in timetable_objects]
    temp_date_list = [x.date for x in Schedule.objects.filter(id__in=id_list)]
    date_list = list(set(temp_date_list))
    date_list.sort(reverse=True)

    date_int_list = [(x.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(x.weekday()), date_to_integer(x)) for x in date_list]
    context['res'] = date_int_list
    return render(request, 'attendance_check_index.html', context=context)


# 선택한 날짜 별 출석 체크 / 지각 여부 확인
def get_attendance_check(request, date):
    context = {}
    date = integer_to_date(date)
    user_objects = PracticeUser.objects.all()
    # eta/real arrival time 비교 dict -> {날짜 : {사람 : [ETA, 실제 도착 시간, 지각(분)]}}
    attendance_dict = {}
    date_to_string = date.strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(date.weekday())
    attendance_dict[date_to_string] = {}
    for user_object in user_objects:
        arrival_time_object = ArrivalTime.objects.filter(user_name=user_object, date=date)
        eta = calculate_eta(user_object=user_object, date=date)
        late_time = None
        if arrival_time_object:
            arrival_time = arrival_time_object[0].arrival_time
        else:
            arrival_time = None
        if arrival_time and eta:
            delta = (datetime.combine(datetime.today(), arrival_time) - datetime.combine(datetime.today(), eta)).total_seconds()
            late_time = max(int(delta / 60), 0)
        attendance_dict[date_to_string][user_object.username] = [eta, arrival_time, late_time]

    context['res'] = attendance_dict
    return render(request, 'get_attendance.html', context=context)


@login_required(login_url=URL_LOGIN)
def setting(request):
    message = None
    context = {}
    if request.method == "POST":
        res = dict(request.POST)
        schedule_objects = Schedule.objects.all()
        schedule_objects.update(is_current=False)
        if 'schedule_checkbox' in res:
            Schedule.objects.filter(id__in=res['schedule_checkbox']).update(is_current=True)
        for schedule_object in schedule_objects:
            idx = schedule_object.id
            Schedule.objects.filter(id=idx).update(min_per_song=int(res['minute_' + str(idx)][0]), rooms=int(res['rooms_' + str(idx)][0]))
        message = "변경되었습니다."

    schedules = Schedule.objects.all().order_by('date')

    current_schedule_objects = Schedule.objects.filter(is_current=True).order_by('date')
    temp_not_submitted_list = []
    for current_schedule_object in current_schedule_objects:
        not_submitted = PracticeUser.objects.filter(~Exists(Apply.objects.filter(user_name=OuterRef('pk'), schedule_id=current_schedule_object)))
        temp_not_submitted_list.extend([i.username for i in not_submitted])

    not_submitted_list = list(set(temp_not_submitted_list))
    not_submitted_list.sort()

    context['message'] = message
    context['schedules'] = schedules
    context['not_submitted'] = not_submitted_list

    return render(request, 'setting.html', context=context)


@login_required(login_url=URL_LOGIN)
def schedule_create(request):
    context = {}
    message = None
    form = ScheduleCreateForm()
    if request.method == "POST":
        form = ScheduleCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('setting')
        else:
            message = form.non_field_errors()[0]
            form = ScheduleCreateForm(request.POST)

    context['form'] = form
    context['message'] = message
    return render(request, 'schedule_create.html', context=context)


@login_required(login_url=URL_LOGIN)
def schedule_delete(request, schedule_id):
    practice_to_delete = get_object_or_404(Schedule, id=schedule_id)
    practice_to_delete.delete()
    return redirect('setting')


@login_required(login_url=URL_LOGIN)
def song_list(request):
    context = {}
    form = SongAddForm
    message = None
    # 곡 추가하는 경우
    if request.method == "POST" and 'add' in request.POST:
        form = SongAddForm(request.POST)
        # forms에서 validation 진행
        if form.is_valid():
            form.save()
            form = SongAddForm()
            message = "등록되었습니다."
        else:
            message = form.non_field_errors()[0]
            form = SongAddForm(request.POST)

    # 곡 삭제하는 경우
    if request.method == "POST" and 'delete' in request.POST:
        # 체크된 곡들 삭제하기
        delete_ids = request.POST.getlist('song_id')
        if delete_ids:
            d = SongData.objects.filter(id__in=delete_ids)
            try:
                d.delete()
                message = "삭제되었습니다."
            except:
                message = "삭제에 실패하였습니다. 다시 시도해주세요."
        else:
            message = "하나 이상의 곡을 선택해주세요."

    # 곡의 합주 우선순위 업데이트
    if request.method == "POST" and 'updateId' in request.POST and request.POST['updateId']:
        res = dict(request.POST)
        update_Id = res['updateId'][0]
        update_value = res[update_Id][0]
        u = SongData.objects.filter(id=update_Id).update(priority=update_value)

    # 곡 목록 보여주기
    songs = SongData.objects.all().order_by('songname')
    song_dict = {}
    for song in songs:
        session_dict = defaultdict(list)
        sessions = song.session.all()
        for s in sessions:
            session_dict[s.instrument].append(s.user_name.username)
        session_dict = {key: ", ".join(val) for key, val in session_dict.items()}
        # 각 곡별 세션 데이터를 딕셔너리로 정리
        song_dict[song] = dict(session_dict)
    context['songs'] = song_dict
    context['form'] = form
    context['message'] = message
    return render(request, 'song_list.html', context=context)


@login_required(login_url=URL_LOGIN)
def user_list(request):
    form = UserAddForm()
    context = {}
    message = None

    # 인원 추가하는 경우
    if request.method == "POST" and 'add' in request.POST:
        form = UserAddForm(request.POST)
        if form.is_valid():
            form.save()
            message = "추가되었습니다."
            form = UserAddForm()

        else:
            message = form.non_field_errors()[0]
            form = UserAddForm(request.POST)

    # 인원 삭제하는 경우
    if request.method == "POST" and 'delete' in request.POST:
        # 체크된 인원들 삭제하기
        delete_names = request.POST.getlist('user_name')
        if delete_names:
            d = PracticeUser.objects.filter(username__in=delete_names)
            if d:
                d.delete()
                message = "삭제되었습니다."
            else:
                # 선택된 유저가 존재하지 않는 경우
                message = "삭제에 실패하였습니다. 다시 시도해주세요."
        else:
            # 웹 상에서 체크를 하지 않은 경우
            message = "하나 이상의 인원을 선택해주세요."

    # 전체 인원 목록 가져와 보여주기
    users = PracticeUser.objects.all().order_by('username')

    context['form'] = form
    context['message'] = message
    context['users'] = users
    return render(request, 'user_list.html', context=context)


@login_required(login_url=URL_LOGIN)
def timetable(request):
    context = {}
    message = None

    # 시간표, 동선 최적화 위한 공통 데이터 가져오기
    base_retriever = BaseRetriever()
    common_data = base_retriever.retreive_common_data()

    # 시간표 최적화 위한 데이터 가져오기
    schedule_retriever = ScheduleRetriever()
    raw_data = schedule_retriever.retrieve_from_DB(common_data=common_data)

    # 시간표 최적화 위한 전처리 과정
    schedule_processor = ScheduleProcessor(raw_data)
    processed_data = schedule_processor.process()

    # 시간표를 db 저장하기 위해 timetable object로 변환하기 위한 데이터 가져오기
    info_dict = processed_data['practice_info_dict']
    song_objects = raw_data['song_objects']
    practiceId_to_date = processed_data['practiceId_to_date']

    # 시간표 optimizer을 이용한 최적화
    schedule_optimizer = ScheduleOptimizer(processed_data)
    result = schedule_optimizer.optimize()

    # 최적화된 시간표를 후처리하여 시간표를 dataframe로, 불참 인원과 사유를 dictionary로 반환
    schedule_postprocessor = SchedulePostProcessor(result, processed_data)
    schedule_df_dict, who_is_not_coming = schedule_postprocessor.post_process()

    # 웹의 가독성을 위해 dataframe의 Nan을 'X'로 변경
    schedule_df_dict = {i: v.fillna("X") for i, v in schedule_df_dict.items()}

    # 동선 최적화 위한 데이터 가져오기
    route_retriever = RouteRetriever()
    raw_data = route_retriever.retrieve_db_data(common_data=common_data)

    for i,df in schedule_df_dict.items():
        # 동선 최적화 위한 전처리 과정
        route_processor = RouteProcessor(raw_data, df)
        processed_data = route_processor.process()

        # 동선 optimizer을 이용한 최적화
        route_optimizer = RouteOptimizer(processed_data, raw_data)
        result = route_optimizer.optimize()

        # 동선 최적화된 시간표를 후처리하여 시간표를 dataframe로 반환
        route_postprocessor = RoutePostProcessor(route_optimizer, df)
        new_dataframe = route_postprocessor.post_process()

        schedule_df_dict[i] = new_dataframe

    # 웹 가독성을 위해 시간표들의 dictionary의 키를 Song id -> Song name으로 변환
    schedule_df_result = {}
    for i, v in schedule_df_dict.items():
        schedule_df_result[practiceId_to_date[i]] = [i,v]

    context['df'] = schedule_df_result
    context['NA'] = who_is_not_coming

    # 불참 여부 미제출 인원 체크하기
    schedule_objects = schedule_processor.raw_data['schedule_objects']
    for schedule_object in schedule_objects:
        not_submitted = PracticeUser.objects.filter(~Exists(Apply.objects.filter(user_name=OuterRef('pk'), schedule_id=schedule_object)))
        if not_submitted:
            message = "아직 불참 여부를 제출하지 않은 인원이 존재합니다!"

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
        timetable_object_dict = timetable_df_to_objects(schedule_df_dict, info_dict, song_objects)

        for schedule_id, v in timetable_object_dict.items():
            schedule_id = Schedule.objects.get(id=schedule_id)
            existing_timetable_object = Timetable.objects.filter(schedule_id=schedule_id)
            # DB에 존재하는 해당 합주 시간표 조회 후 삭제
            if existing_timetable_object:
                existing_timetable_object.delete()

            # Bulk 저장
            timetable_object_list = [Timetable(schedule_id=schedule_id, song_id=SongData.objects.get(id=song_id), start_time=info_tuple[0], end_time=info_tuple[1], room_name=info_tuple[2]) for song_id, info_tuple in v.items()]
            Timetable.objects.bulk_create(timetable_object_list)
            message = "저장되었습니다."

    context['message'] = message
    return render(request, 'timetable.html', context=context)


@login_required(login_url=URL_LOGIN)
def who_is_not_coming(request):
    # 불참 시간과 사유
    context = {}
    current_schedule = Schedule.objects.filter(is_current=True)
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
                name = i.user_name.username
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
            reason_object = WhyNotComing.objects.filter(schedule_id=schedule)
            for i in reason_object:
                reason_why[schedule_id][i.user_name.username] = i.reason

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


@login_required(login_url=URL_LOGIN)
def metrics(request):
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
