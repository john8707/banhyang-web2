from django.shortcuts import render, redirect, get_object_or_404
from .forms import PracticeApplyForm, PracticeCreateForm, SongAddForm, UserAddForm, validate_user_exist
from .models import Schedule, SongData, PracticeUser, Apply, Session
from datetime import timedelta, date, datetime, time
from django.contrib import messages
from .schedule import ScheduleOptimizer
from django.contrib.auth.decorators import login_required
from collections import defaultdict

# TODO 
# 1. 관리 화면 첫 화면에서 메인 노출 날짜 삭제하기
# 4. 시간 선택 디자인 변경

def practice(request):
    weekday_dict = {
        0: ' (월)',
        1: ' (화)',
        2: ' (수)',
        3: ' (목)',
        4: ' (금)',
        5: ' (토)',
        6: ' (일)'
    }

    # Schedule에서 현재 활성화 되어있는 합주 날짜를 가져온다.
    current_practice = Schedule.objects.filter(is_current=True)
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
            while temp_time + timedelta(minutes=10) <= endtime:

                # 각 날짜별 첫번째 iteration의 choice의 value 값을 0으로 설정하고 string은 해당 날짜로 -> html에서 choice를 iteration 돌릴 때, value가 0인 경우는 choice로 안나옴  -> 수정 필요
                if div_for_day == 0:
                    # HTML 상 날짜 추가 용
                    choice.append((0, "%s (%s~%s)"%(i.date.strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') +weekday_dict[i.date.weekday()], i.starttime.strftime("%H:%M"), i.endtime.strftime("%H:%M"))))
                    
                    # 전체 참가 선택지 추가
                    choice.append((-1, str(i.id) + "_" + "-1"))
                
                choice.append((str(i.id) + "_" + str(div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=10)).strftime("%H:%M"))))
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
            practiceId_list = [x.id for x in practice_objects]

            is_validate = True
            for i in practiceId_list:
                selected_dict[i] = [int(x.split('_')[1]) for x in selected if int(x.split('_')[0]) == i]
                # 최소 한 개 선택
                if selected_dict[i] == []:
                    is_validate = False
                    message = "불참 시간 혹은 전체 참여를 각 날짜별로 선택해주세요."
                # 참여 혹은 불참 
                elif -1 in selected_dict[i] and len(selected_dict[i]) > 1:
                    is_validate = False
                    message = "불참 혹은 전체 참여 중 1가지만 선택하여주세요."

            if is_validate:
                Apply.objects.filter(user_name=form.cleaned_data['user_object']).delete()
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


@login_required
def setting(request):
    message = None
    if request.method == "POST":
        res = dict(request.POST)
        Schedule.objects.all().update(is_current=False)
        if 'test' in res:
            Schedule.objects.filter(id__in=res['test']).update(is_current=True)
        message = "변경되었습니다."
            
    schedules = Schedule.objects.all().order_by('date')


    user_objects = PracticeUser.objects.all()
    practice_objects = Schedule.objects.filter(is_current=True).order_by('date')
    not_submitted_list = []
    for i in user_objects:
        for j in practice_objects:
            submitted = Apply.objects.filter(user_name=i, schedule_id=j)
            if not submitted and i.username not in not_submitted_list:
                not_submitted_list.append(i.username)
    print(not_submitted_list)            

    return render(request, 'setting.html', {'schedules' : schedules, 'not_submitted': not_submitted_list, 'message': message})


@login_required
def create(request):
    #TODO 어떻게 추가하는지 써놓기(시간은 가능한 한 시간 or 삼십분 단위로 할 것)
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


@login_required
def practice_delete(request, schedule_id):
    practice_to_delete = get_object_or_404(Schedule, id = schedule_id)
    practice_to_delete.delete()
    return redirect('setting')


@login_required
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
    # 곡 목록 보여주기
    songs = SongData.objects.all().order_by('songname')
    song_dict = {}
    for song in songs:
        session_dict = defaultdict(list)
        sessions = song.session.all()
        for s in sessions:
            session_dict[s.instrument].append(s.user_name.username)
        session_dict = {key:", ".join(val) for key, val in session_dict.items()}
        song_dict[song] = dict(session_dict)

    context['songs'] = song_dict
    context['form'] = form
    context['message'] = message
    return render(request, 'song_list.html', context=context)



@login_required
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



@login_required
def schedule_create(request):
    context = {}
    message = None
    s = ScheduleOptimizer()
    s.create_schedule()
    df_list, who_is_not_coming = s.post_processing()
    df_list = {i:v.fillna("X") for i,v in df_list.items()}
    context['df'] = df_list
    context['NA'] = who_is_not_coming
    return render(request, 'schedule_create.html', context=context)


@login_required
def who_is_not_coming(request):
    context = {}
    current_schedule = Schedule.objects.filter(is_current=True)
    if current_schedule:
        not_available = {}
        for schedule in current_schedule:
            na = schedule.apply.all()
            schedule_date = schedule.date.strftime("%y/%m/%d - " + str(schedule.id))
            not_available[schedule_date] = defaultdict(list)
            for i in na:
                name = i.user_name.username
                time = i.not_available
                not_available[schedule_date][name].append(time)

    else:
        not_available = None
    
    context['NA'] = not_available
    return render(request, 'who_is_not_coming.html', context=context)