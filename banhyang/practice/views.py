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
                    choice.append((0, "%s (%s~%s)"%(i.date.strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape'), i.starttime.strftime("%H:%M"), i.endtime.strftime("%H:%M"))))
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
            Apply.objects.filter(user_name=form.cleaned_data['user_object']).delete()

            if 'selected' in res:
                selected = res['selected']
                for i in selected:
                    schedule_object = Schedule.objects.get(id=i.split('_')[0])
                    a = Apply(user_name=form.cleaned_data['user_object'], schedule_id=schedule_object, not_available=i.split('_')[1])
                    a.save()
                
            message = "제출되었습니다."
            form = PracticeApplyForm()
        
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
    return render(request, 'setting.html', {'schedules' : schedules, 'message': message})


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
    #preprocessing()
    if request.method == "POST":
        # 곡 추가하는 경우
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
            message = "등록되었습니다"
        # validation error
        else:
            message = form.non_field_errors()[0]
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
def song_delete(request, song_id):
    song_to_delete = get_object_or_404(SongData, id = song_id)
    song_to_delete.delete()
    return redirect('song_list')


@login_required
def user_list(request):
    if request.method == "POST":
        form = UserAddForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.save()
            return redirect('user_list')
    else:
        form = UserAddForm()
        users = PracticeUser.objects.all().order_by('username')
        return render(request, 'user_list.html', {'users' :users, 'form' :form})


@login_required
def user_delete(request, username):
    user_to_delete = get_object_or_404(PracticeUser, username = username)
    user_to_delete.delete()
    return redirect('user_list')


@login_required
def schedule_create(request):
    context = {}
    message = None
    s = ScheduleOptimizer()
    s.create_schedule()
    df_list, who_is_not_coming = s.post_processing()
    context['df'] = df_list
    context['NA'] = who_is_not_coming
    return render(request, 'schedule_create.html', context=context)


@login_required
def who_is_not_coming(request):
    current_schedule = Schedule.objects.filter(is_current=True)
    if current_schedule:
        not_available = {}
        for schedule in current_schedule:
            na = schedule.apply.all()
            schedule_date = schedule.date.strftime("%m/%d - " + str(schedule.id))
            not_available[schedule_date] = defaultdict(list)
            for i in na:
                name = i.user_name.username
                time = i.not_available
                not_available[schedule_date][name].append(time)
        
    else:
        not_available = None
    return render(request, 'who_is_not_coming.html', {'NA' : not_available})