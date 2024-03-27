from django.shortcuts import render, redirect, get_object_or_404
from .forms import PracticeApplyForm, PracticeCreateForm, SongAddForm, UserAddForm, validate_user_exist, AttendanceCheckForm
from .models import Schedule, SongData, PracticeUser, Apply, Session, WhyNotComing, Timetable, AttendanceCheck
from datetime import timedelta, date, datetime, time
from django.contrib import messages
from django.db.models import Exists, OuterRef
from .schedule import ScheduleOptimizer
from django.contrib.auth.decorators import login_required
from collections import defaultdict

URL_LOGIN = '/admin/'
def weekday_dict(idx):
    weekday_to_korean = {
        0: ' (월)',
        1: ' (화)',
        2: ' (수)',
        3: ' (목)',
        4: ' (금)',
        5: ' (토)',
        6: ' (일)'
    }
    return weekday_to_korean[idx]


def practice(request):
    # Schedule에서 현재 활성화 되어있는 합주 날짜를 가져온다.
    current_practice = Schedule.objects.filter(is_current=True).order_by('date')
    message = None
    # 활성화 된 합주 날짜가 존재할 경우
    if len(current_practice):
        choice = []
        for i in current_practice:
            # 시작 시간
            temp_time = datetime.combine(date.today(), i.starttime)
            # 끝나는 시간
            endtime = datetime.combine(date.today(), i.endtime)


            # 각 날짜별 division counter, (ex 합주 시간이 3시~4시 / 곡 당 시간이 30분일 경우 3시 = 0, 3시 30분 = 1)
            div_for_day = 0
            
            # temp time이 endtime을 넘지 않을 때 까지 10분을 temp time에 더하면서 반복
            while temp_time < endtime:

                # 각 날짜별 첫번째 iteration의 choice의 value 값을 0으로 설정하고 string은 해당 날짜로 -> html에서 choice를 iteration 돌릴 때, value가 0인 경우는 choice로 안나옴  -> 수정 필요
                if div_for_day == 0:
                    # HTML 상 날짜 추가 용
                    choice.append((0, "%s (%s~%s)"%(i.date.strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') +weekday_dict(i.date.weekday()), i.starttime.strftime("%H:%M"), i.endtime.strftime("%H:%M"))))
                    
                    # 전체 참가 선택지 추가
                    choice.append((-1, str(i.id) + "_" + "-1"))
                if temp_time + timedelta(minutes=10) <= endtime:
                    choice.append((str(i.id) + "_" + str(div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=10)).strftime("%H:%M"))))
                else:
                    choice.append((str(i.id) + "_" + str(div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (endtime).strftime("%H:%M"))))
                temp_time += timedelta(minutes=10)
                div_for_day += 1

        form = PracticeApplyForm()
    # 활성화 된 합주가 없을 경우 Return Nothing
    else:
        form = None
        choice = None

    # SUBMIT 했을 시
    if request.method == "POST":
        form = PracticeApplyForm(request.POST)
        if form.is_valid():
            res = dict(request.POST)
            username = res['username'][0]
            practice_objects = Schedule.objects.filter(is_current=True).order_by('date')

            # validation
            selected = []
            if 'selected' in res:
                selected = res['selected']
            selected_dict = {}
            reason_dict = {}
            practiceId_list = [x.id for x in practice_objects]

            is_validate = True
            for i in practiceId_list:
                selected_dict[i] = [int(x.split('_')[1]) for x in selected if int(x.split('_')[0]) == i]
                reason_dict[i] = res['why_not_coming_' + str(i) + '_-1'][0]

                # 최소 한 개 선택
                if selected_dict[i] == []:
                    message = "불참 시간 혹은 전체 참여를 각 날짜별로 선택해 주세요."
                    is_validate = False
                
                # 불참인데 사유를 입력하지 않은 경우
                elif reason_dict[i] == '' and len(selected_dict[i]) > 1:
                    message = "불참 사유를 입력해 주세요"
                    is_validate = False
                
                # 참여 혹은 불참 
                elif -1 in selected_dict[i] and len(selected_dict[i]) > 1:
                    message = "불참 혹은 전체 참여 중 1가지만 선택해 주세요."
                    is_validate = False

                # 전체 참여인데 불참 사유가 존재하는 경우 -> 사유 지우기
                if -1 in selected_dict[i]:
                    reason_dict[i] = ""

            # 모든 Validation 통과하고 DB 업데이트
            if is_validate:
                Apply.objects.filter(user_name=form.cleaned_data['user_object']).delete()
                WhyNotComing.objects.filter(user_name=form.cleaned_data['user_object']).delete()

                for k,v in reason_dict.items():
                    if v:
                        schedule_object = Schedule.objects.get(id=k)
                        w = WhyNotComing(user_name=form.cleaned_data['user_object'], schedule_id=schedule_object, reason=v)
                        w.save()
                # validation 이후 제출
                for i in selected:
                    schedule_object = Schedule.objects.get(id=i.split('_')[0])
                    a = Apply(user_name=form.cleaned_data['user_object'], schedule_id=schedule_object, not_available=i.split('_')[1])
                    a.save()
                
            
                message = "제출되었습니다."
                form = PracticeApplyForm()
            
            else:
                form = PracticeApplyForm(request.POST)
        
        else:
            message = form._errors['message']



    return render(request, 'practice.html', {'form' : form, 'choices' : choice, 'message' : message})


def attendance_check(request):
    form = AttendanceCheckForm()
    message = ''
    context = {}

    attendance_dict ={}
    # 춣석/지각 여부 dict -> {schedule id : {timetable id : {출석:[],지각:[],불참/미인증:[]}}}

    schedule_objects = Schedule.objects.all().order_by('-date')
    for schedule_object in schedule_objects:
        attendance_per_tt_dict = {}
        timetable_objects = schedule_object.timetable.all().order_by('start_time')
        for timetable_object in timetable_objects:
            session_objects = Session.objects.filter(song_id=timetable_object.song_id).distinct().values_list('user_name')

            user_list= [x[0] for x in session_objects]

            attendance_per_tt_dict[timetable_object] = {'출석':[],'지각':[],'미인증/불참':[]}
            attendance_objects = AttendanceCheck.objects.filter(timetable_id=timetable_object)
            for user_name in user_list:
                user_object = PracticeUser.objects.get(username=user_name)
                try:
                    attendance_object = attendance_objects.get(user_name=user_object)
                    arrival = datetime.combine(date.today(), attendance_object.arrival_time)
                    # 5분까지 지각 허용
                    due = datetime.combine(date.today(), timetable_object.start_time) + timedelta(minutes=6)
                    if  arrival > due:
                        late = arrival - due
                        late_minute = int(late.seconds/60) + 1
                        attendance_per_tt_dict[timetable_object]['지각'].append(user_object.username + " ("+ str(late_minute) + "분)")
                    else:
                        attendance_per_tt_dict[timetable_object]['출석'].append(user_object.username)

                except AttendanceCheck.DoesNotExist:
                    attendance_per_tt_dict[timetable_object]['미인증/불참'].append(user_object.username)
            
        

        date_to_string = schedule_object.date.strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(schedule_object.date.weekday())
        attendance_dict[date_to_string] = attendance_per_tt_dict


    
    
    if request.method == "POST":
        form = AttendanceCheckForm(request.POST)
        if form.is_valid():
            # Validation 과정 -> forms.ArrivalAddForm에서 진행
            user_object, timetable_objects, now = form.cleaned_data

            attendance_object_list = [AttendanceCheck(user_name = user_object, timetable_id=x) for x in timetable_objects]
            AttendanceCheck.objects.bulk_create(attendance_object_list)
            message = '출석 확인 되었습니다.'

            form = AttendanceCheckForm()
        else:
            message = form.non_field_errors()[0]
    context['form'] = form
    context['message'] = message
    context['res'] = attendance_dict

    return render(request, 'attendance_check.html',context=context)


@login_required(login_url=URL_LOGIN)
def setting(request):
    message = None
    if request.method == "POST":
        res = dict(request.POST)
        schedule_object = Schedule.objects.all()
        schedule_object.update(is_current=False)
        if 'schedule_checkbox' in res:
            Schedule.objects.filter(id__in=res['schedule_checkbox']).update(is_current=True)
        for obj in schedule_object:
            idx = obj.id
            Schedule.objects.filter(id=idx).update(min_per_song=int(res['minute_'+str(idx)][0]), rooms=int(res['rooms_'+str(idx)][0]))
        message = "변경되었습니다."
            
    schedules = Schedule.objects.all().order_by('date')


    practice_objects = Schedule.objects.filter(is_current=True).order_by('date')
    not_submitted_list = []
    for practice_object in practice_objects:
        not_submitted = PracticeUser.objects.filter(~Exists(Apply.objects.filter(user_name=OuterRef('pk'), schedule_id=practice_object)))
        not_submitted_list.extend([i.username for i in not_submitted])

    u_not_submitted_list = list(set(not_submitted_list))
    u_not_submitted_list.sort()

    return render(request, 'setting.html', {'schedules' : schedules, 'not_submitted': u_not_submitted_list, 'message': message})


@login_required(login_url=URL_LOGIN)
def create(request):
    if request.method == "POST":
        form = PracticeCreateForm(request.POST)
        if form.is_valid() and form.cleaned_data['starttime'] < form.cleaned_data['endtime']:
            f = form.save(commit=False)
            f.date = form.cleaned_data['date'] + timedelta(hours=9)
            f.min_per_song = form.cleaned_data['minutes']
            f.starttime = form.cleaned_data['starttime']
            f.endtime = form.cleaned_data['endtime']
            f.save()
            return redirect('practice')
    else:
        form = PracticeCreateForm()

    return render(request, 'create.html', {'form' : form})


@login_required(login_url=URL_LOGIN)
def practice_delete(request, schedule_id):
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
    s = ScheduleOptimizer()
    s.create_schedule()
    df_list, who_is_not_coming, timetable_object_dict = s.post_processing()
    df_list = {i:v.fillna("X") for i,v in df_list.items()}
    context['df'] = df_list
    context['NA'] = who_is_not_coming

    # 불참 여부 미제출 인원 체크하기
    practice_objects = Schedule.objects.filter(is_current=True).order_by('date')
    for practice_object in practice_objects:
        not_submitted = PracticeUser.objects.filter(~Exists(Apply.objects.filter(user_name=OuterRef('pk'), schedule_id=practice_object)))
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
                message = "저장에 실패하였습니다. 관리자에게 문의하세요." + E

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