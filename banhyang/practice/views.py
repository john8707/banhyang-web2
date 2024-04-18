from django.shortcuts import render, redirect, get_object_or_404
from .forms import PracticeApplyForm, ScheduleCreateForm, SongAddForm, UserAddForm
from .models import Schedule, SongData, PracticeUser, Apply, Session, WhyNotComing, Timetable, ArrivalTime
from datetime import timedelta, date, datetime, time, timezone
from django.contrib import messages
from django.db.models import Exists, OuterRef
from .schedule import ScheduleRetreiver, ScheduleProcessor, ScheduleOptimizer, SchedulePostProcessor
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from banhyang.core.utils import weekday_dict, calculate_eta, date_to_integer, integer_to_date
URL_LOGIN = '/admin/login/?next=/practice/setting'


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
    message = ''
    context = {}

    timetable_objects = Timetable.objects.distinct().values('schedule_id')
    id_list = [x['schedule_id'] for x in timetable_objects]
    temp_date_list = [x.date for x in Schedule.objects.filter(id__in=id_list)]
    date_list = list(set(temp_date_list))
    date_list.sort(reverse=True)

    date_int_list = [(x.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(x.weekday()), date_to_integer(x)) for x in date_list]
    context['res'] = date_int_list
    return render(request, 'attendance_check_index.html',context=context)


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
        arrival_time_object = ArrivalTime.objects.filter(user_name=user_object,date=date)
        eta = calculate_eta(user_object=user_object, date=date)
        delta = None
        if arrival_time_object:
            arival_time = arrival_time_object[0].arrival_time
        else:
            arival_time = None
        if arival_time and eta:
            #delta : 몇 분 지각했는지 구하기
            delta = (datetime.combine(datetime.today(), arival_time) - datetime.combine(datetime.today(), eta)).total_seconds()
            late_time = max(int(delta/60), 0)
        attendance_dict[date_to_string][user_object.username] = [eta,arival_time,late_time]

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
            Schedule.objects.filter(id=idx).update(min_per_song=int(res['minute_'+str(idx)][0]), rooms=int(res['rooms_'+str(idx)][0]))
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
    if request.method == "POST":
        form = ScheduleCreateForm(request.POST)
        if form.is_valid() and form.cleaned_data['starttime'] < form.cleaned_data['endtime']:
            f = form.save(commit=False)
            f.date = form.cleaned_data['date'] + timedelta(hours=9)
            f.min_per_song = form.cleaned_data['minutes']
            f.starttime = form.cleaned_data['starttime']
            f.endtime = form.cleaned_data['endtime']
            f.save()
            return redirect('setting')
    else:
        form = ScheduleCreateForm()

    return render(request, 'schedule_create.html', {'form' : form})


@login_required(login_url=URL_LOGIN)
def schedule_delete(request, schedule_id):
    practice_to_delete = get_object_or_404(Schedule, id = schedule_id)
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
            f = form.cleaned_data
            SongData.objects.filter(songname=f['song_name']).delete()

            # 곡의 제목부터 저장
            s = SongData(songname=f['song_name'])
            s.save()
            session_index = {'vocals':'v','drums':'d','guitars':'g','bass':'b','keyboards':'k','etc':'etc'}
            # 곡의 세션들 저장
            for key,values in f.items():
                if key != 'song_name':
                    for user in values:
                        se = Session(song_id=s,user_name=user,instrument=session_index[key])
                        se.save()
            form = SongAddForm()
            message = "등록되었습니다."
        # validation error
        else:
            message = form.non_field_errors()[0]
    
    # 곡 삭제하는 경우
    if request.method == "POST" and 'delete' in request.POST:
        # 체크된 곡들 삭제하기
        delete_ids = request.POST.getlist('song_id')
        if delete_ids:
            d = SongData.objects.filter(id__in=delete_ids)
            if d:
                d.delete()
                message = "삭제되었습니다."
            else:
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
        session_dict = {key:", ".join(val) for key, val in session_dict.items()}
        # 각 곡별 세션 데이터를 딕셔너리로 정리
        song_dict[song] = dict(session_dict)
    context['songs'] = song_dict
    context['form'] = form
    context['message'] = message
    return render(request, 'song_list.html', context=context)



@login_required(login_url=URL_LOGIN)
def user_list(request):
    form = UserAddForm()
    context={}
    message = None

    #인원 추가하는 경우
    if request.method == "POST" and 'add' in request.POST:
        form = UserAddForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            s = PracticeUser(username = f['username'])
            s.save()
            message = "추가되었습니다."
            form = UserAddForm()

        else:
            message = form.non_field_errors()[0]

    #인원 삭제하는 경우
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

    #전체 인원 목록 가져와 보여주기
    users = PracticeUser.objects.all().order_by('username')
    
    #html 전달 context
    context['form'] = form
    context['message'] = message
    context['users'] = users
    return render(request, 'user_list.html', context=context)



@login_required(login_url=URL_LOGIN)
def timetable(request):
    context = {}
    message = None
    retreiever = ScheduleRetreiver()
    raw_data = retreiever.retreive_from_DB()
    processor = ScheduleProcessor(raw_data)
    processed_data = processor.process()
    optimizer = ScheduleOptimizer(processed_data)
    result = optimizer.optimize()
    postprocessor = SchedulePostProcessor(result, processed_data)
    df_list, who_is_not_coming, timetable_object_dict = postprocessor.post_process()

    df_list = {i:v.fillna("X") for i,v in df_list.items()}
    context['df'] = df_list
    context['NA'] = who_is_not_coming

    # 불참 여부 미제출 인원 체크하기
    schedule_objects = Schedule.objects.filter(is_current=True).order_by('date')
    for schedule_object in schedule_objects:
        not_submitted = PracticeUser.objects.filter(~Exists(Apply.objects.filter(user_name=OuterRef('pk'), schedule_id=schedule_object)))
        if not_submitted : message = "아직 불참 여부를 제출하지 않은 인원이 존재합니다!"


    if request.method == "POST":
        for schedule_id, v in timetable_object_dict.items():
            schedule_id = Schedule.objects.get(id=schedule_id)
            existing_timetable_object = Timetable.objects.filter(schedule_id=schedule_id)
            # DB에 존재하는 해당 합주 시간표 조회 후 삭제
            if existing_timetable_object:
                existing_timetable_object.delete()


            # Bulk 저장
            timetable_object_list = [Timetable(schedule_id = schedule_id, song_id=SongData.objects.get(id=song_id), start_time=info_tuple[0], end_time=info_tuple[1], room_number=info_tuple[2]) for song_id, info_tuple in v.items()]
            try:
                Timetable.objects.bulk_create(timetable_object_list)
                message = "저장되었습니다."
            except Exception as E:
                message = "저장에 실패하였습니다. 관리자에게 문의하세요."

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
                'id' : schedule.id,
                'date' : schedule.date.strftime("%y/%m/%d"),
                'starttime' : schedule.starttime,
                'endtime' : schedule.endtime
            }
            na = schedule.apply.all()
            schedule_id = schedule.id
            not_available[schedule_id] = defaultdict(list)
            # 불참 시간 정리(가공 전)
            for i in na:
                name = i.user_name.username
                time = i.not_available
                not_available[schedule_id][name].append(time)
            schedule_start_time =  datetime.combine(date.today(),schedule.starttime)
            
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
                    if j == None:
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
            sorted_dict = sorted(when_and_why[date_to_string].items(), key = lambda item: item[1])
            when_and_why[date_to_string] = sorted_dict
            
    else:
        when_and_why = None
    



    context['when_and_why'] = when_and_why

    return render(request, 'who_is_not_coming.html', context=context)