from django.shortcuts import render, redirect, get_object_or_404
from .forms import PracticeApplyForm, PracticeCreateForm, SongAddForm
from .models import Schedule, SongData
from datetime import timedelta, date, datetime, time


# TODO 
# 1. 관리 화면 첫 화면에서 메인 노출 날짜 선택하기, 삭제하기
# 2. 유저 등록/수정
# 3. 유저 제출시 db에 업데이트
# 4. 시간 선택 디자인 변경

def practice(request):
    if request.method == "POST":
        #TODO DB에 업데이트 하기!
        form = PracticeApplyForm(request.POST)
        return redirect('practice')
    else:
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
                        choice.append(((i.id, div_for_day),"%s - %s, (%s)"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"), temp['date'].strftime('%m/%d'))))
                    else:
                        choice.append(((i.id, div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"))))
                    temp_time += timedelta(minutes=time_per_song)
                    div_for_day += 1

                choice.append(((i.id, div_for_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"))))

                res[i.id] = temp
            form = PracticeApplyForm(choices=choice)
        
        else:
            form = None
        
        return render(request, 'practice.html', {'form' : form})


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


def song_list(request):
    if request.method == "POST":
        form = SongAddForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.save()
            return redirect('song_list')
    else:
        form = SongAddForm()
        songs = SongData.objects.all()
        return render(request, 'song_list.html', {'songs' :songs, 'form' :form})


def song_delete(request, song_id):
    song_to_delete = get_object_or_404(SongData, id = song_id)
    song_to_delete.delete()
    return redirect('song_list')
