from django.shortcuts import render, redirect, get_object_or_404
from .forms import PracticeApplyForm, PracticeCreateForm, SongAddForm, UserAddForm, validate_user_exist
from .models import Schedule, SongData, PracticeUser, Apply
from datetime import timedelta, date, datetime, time
from django.contrib import messages
from .schedule import Create
from django.contrib.auth.decorators import login_required
# TODO 
# 1. 관리 화면 첫 화면에서 메인 노출 날짜 삭제하기
# 4. 시간 선택 디자인 변경

def practice(request):
    current_practice = Schedule.objects.filter(is_current=True)
    if len(current_practice):
        res = {}
        choice = []
        for i in current_practice:
            temp = {}
            temp['name'] = i.name
            temp['date'] = i.date
            temp['time_list'] = []
            temp_time = datetime.combine(date.today(), i.starttime)
            endtime = datetime.combine(date.today(), i.endtime)
            time_per_song = 60 / i.div
            div_for_day = 0
            while  temp_time + timedelta(minutes=time_per_song) < endtime:
                if div_for_day == 0:
                    choice.append((0, "%s"%(temp['date'].strftime('%m월%d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape'))))
                    choice.append((str(i.id) + "_" + str(div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"))))
                else:
                    choice.append((str(i.id) + "_" + str(div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"))))
                temp_time += timedelta(minutes=time_per_song)
                div_for_day += 1

            choice.append((str(i.id) + "_" + str(div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"))))
            res[i.id] = temp
        form = PracticeApplyForm()
    else:
        form = None
        choice = None

    if request.method == "POST":
        form = PracticeApplyForm(request.POST)
        if form.is_valid():
            res = dict(request.POST)
            username = res['username'][0]
            number = res['number'][0]
            Apply.objects.filter(user_name=form.cleaned_data['user_object']).delete()

            if 'selected' in res:
                selected = res['selected']
                for i in selected:
                    schedule_object = Schedule.objects.get(id=i.split('_')[0])
                    a = Apply(user_name=form.cleaned_data['user_object'], schedule_id=schedule_object, not_available=i.split('_')[1])
                    a.save()
                
                messages.success(request, "제출되었습니다")

            return redirect('practice')

    return render(request, 'practice.html', {'form' : form, 'choices' : choice,})


@login_required
def setting(request):
    message = None
    if request.method == "POST":
        res = dict(request.POST)
        Schedule.objects.all().update(is_current=False)
        if 'test' in res:
            Schedule.objects.filter(id__in=res['test']).update(is_current=True)
        message = "변경되었습니다."
            
    schedules = Schedule.objects.all().order_by('-date')
    return render(request, 'setting.html', {'schedules' : schedules, 'message': message})


@login_required
def create(request):
    #TODO 어떻게 추가하는지 써놓기(시간은 가능한 한 시간 or 삼십분 단위로 할 것)
    if request.method == "POST":
        form = PracticeCreateForm(request.POST)
        if form.is_valid() and form.cleaned_data['starttime'] < form.cleaned_data['endtime']:
            f = form.save(commit=False)
            f.date = form.cleaned_data['date'] + timedelta(hours=9)
            f.div = form.cleaned_data['minutes']
            f.starttime = form.cleaned_data['starttime']
            f.endtime = form.cleaned_data['endtime']
            f.save()
            return redirect('practice')
    else:
        form = PracticeCreateForm()

    return render(request, 'create.html', {'form' : form})


@login_required
def song_list(request):
    if request.method == "POST":
        form = SongAddForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.save()
        return redirect('song_list')
    else:
        form = SongAddForm()
        songs = SongData.objects.all().order_by('songname')
        return render(request, 'song_list.html', {'songs' :songs, 'form' :form})


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
        users = PracticeUser.objects.all().order_by('gisu', 'username')
        return render(request, 'user_list.html', {'users' :users, 'form' :form})


@login_required
def user_delete(request, username):
    user_to_delete = get_object_or_404(PracticeUser, username = username)
    user_to_delete.delete()
    return redirect('user_list')

@login_required
def schedule_create(request):

    #DB에서 데이터 받아오기
    songs = SongData.objects.all()
    users = PracticeUser.objects.all()
    schedules = Schedule.objects.filter(is_current=True).order_by('date')

    #변수선언
    song_member_dict = {}
    song_member_list = {}
    song_list = []
    song_value = {}
    days = 0
    intervals = {}
    ########TODO 날짜 별 방 갯수 인풋 받기
    room = 2
    ##################################
    # TODO 뺄 곡, 여러번 할 곡, 필수 곡 목록, 세션 별 비중
    song_del_list = []
    song_multiple_dict = {'Congratulations' : 2}
    song_mandatory_list = []
    ##################################
    member_not_available = {}
    member_available_value = {}

    
    for schedule in schedules:
        #날짜별 [시간당 곡 수, 총 시간, 방 갯수]
        days += 1
        time = datetime.combine(date.today(), schedule.endtime) - datetime.combine(date.today(), schedule.starttime)
        intervals[days] = [schedule.div, int(time.seconds/3600), room]

        #불참 인원 받아와서 [(날짜,타임),...]으로 넘기기
        apply_objects = schedule.apply.all()
        for apply_object in apply_objects:
            if apply_object.user_name.username in member_not_available:
                member_not_available[apply_object.user_name.username].append((days, apply_object.not_available))
            else:
                member_not_available[apply_object.user_name.username] = [(days, apply_object.not_available)]
    
    #날짜 당 가능 곡수 중 최대값(방1개 기준)
    times = []
    for i in range(days):
        times.append(intervals[i+1][0] * intervals[i+1][1])
    max_song_per_day = max(times)

    #세션 별 가능 시간 bool 리스트로[[1,1,1,0,...],[1,1,1,0,...],..]
    for user in users:
        member_available_value[user.username] = []
        for day in range(1, days+1):
            member_available_value[user.username].append([])
            for i in range(1, max_song_per_day + 1):
                if intervals[day][0]*intervals[day][1] < i:
                    member_available_value[user.username][day-1].append(0)
                else:
                    member_available_value[user.username][day-1].append(1)

    #불참 시간 적용하기 (위의 bool 리스트에서 해당 타임 0으로)
    for user in member_not_available:
        na_times = member_not_available[user]
        for na_time in na_times:
            member_available_value[user][na_time[0]-1][na_time[1]] = 0
    
    #곡의 세션 딕셔너리
    for song in songs:
        if song not in song_del_list:
            song_member_dict[song.songname] = {
                'vocal1' : song.vocal1.username if song.vocal1 else None,
                'vocal2' : song.vocal2.username if song.vocal2 else None,
                'drum' : song.drum.username if song.drum else None,
                'guitar1' : song.guitar1.username if song.guitar1 else None,
                'guitar2' : song.guitar2.username if song.guitar2 else None,
                'bass' : song.bass.username if song.bass else None,
                'keyboard1' : song.keyboard1.username if song.keyboard1 else None,
                'keyboard2' : song.keyboard2.username if song.keyboard2 else None,
            }
            #곡의 세션 리스트(중복 확인용)
            song_member_list[song.songname] = song_member_dict[song.songname].values()
            #곡 리스트
            song_list.append(song.songname)

    #세션이 겹치는 곡 목록 받아오기
    overlap_member = {}
    for song1 in song_list:
        temp_list = set()
        for song2 in song_list:
            if song1 != song2:
                for member1 in song_member_list[song1]:
                    for member2 in song_member_list[song2]:
                        if member1 == member2 and member1:
                            temp_list.add(song2)
        overlap_member[song1] = temp_list

    overlap_song_list = []
    for song1 in overlap_member:
        for song2 in overlap_member[song1]:
            temp_list=[song1,song2]
            temp_list.sort()
            overlap_song_list.append(temp_list)

    overlap_song_list.sort()

    for i in overlap_song_list:
        if i in overlap_song_list:
            overlap_song_list.remove(i)
    

    #곡 별 시간 별 값
    for song in song_member_list:
        value_list_temp = []
        song_member_temp = song_member_list[song]
        for i in range(days):
            value_list_temp.append([])
            for j in range(max_song_per_day):
                value_total = 0
                value_temp = 0
                for e, session in enumerate(song_member_temp):
                    if session:
                        if e==0 or e==1:
                            #보컬
                            v = 5
                            value_total += member_available_value[session][i][j]*v
                            value_temp += v
                        elif e==2:
                            #드럼
                            d = 5
                            value_total += member_available_value[session][i][j]*d
                            value_temp += d
                        else:
                            value_total += member_available_value[session][i][j]
                            value_temp += 1
                if value_temp == value_total:
                    value_list_temp[i].append(1)
                else:
                    value_list_temp[i].append(round(value_total / value_temp, 4))
        song_value[song] = value_list_temp

    #정보 final dict에 넣고 value array화
    final = {}
    for i, song in enumerate(song_list):
        if song in song_multiple_dict:
            final[i] = [song,song_value[song], [song_multiple_dict[song]]]
        else:
            final[i] = [song,song_value[song], [1]]

    value = []
    for i in range(days):
        value.append([])
        for j in range(max_song_per_day):
            value[i].append([])
            for k in range(len(final)):
                value[i][j].append(final[k][1][i][j])

    my_df, finallist, solver, who_is_not_coming = Create.create(
        days, max_song_per_day, final, value, intervals, overlap_song_list, song_member_list, member_available_value
        )


    print(my_df)
    return render(request, 'schedule_create.html', {'df' : my_df, 'NA' : who_is_not_coming})