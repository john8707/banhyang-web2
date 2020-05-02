from django.shortcuts import render, redirect, get_object_or_404
from .forms import PracticeApplyForm, PracticeCreateForm, SongAddForm
from .models import Schedule, SongData
from datetime import timedelta, date, datetime, time


# Create your views here.

##TODO 눈에 보이고자 하는 날짜 선택하기 -> 관리자가 전체를 볼 수 있게하자
### + 마감 기능, 보이는 날짜 바꾸기
### 한번 생성 시 계산 한 번 한 후 DB에 저장하자. 매번 하면 개느릴 것 같음

def practice(request):
    if request.method == "POST":
        #TODO DB에 업데이트 하기!
        form = PracticeApplyForm(request.POST)
        return redirect('practice')
    else:
        current_practice = Schedule.objects.filter(is_current=True)
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
        
    return render(request, 'practice.html', {'form' : form})


def setting(request):
    return render(request, 'setting.html')


def create(request):
    #TODO 어떻게 추가하는지 써놓기(시간은 가능한 한 시간 or 삼십분 단위로 할 것, )
    if request.method == "POST":
        form = PracticeCreateForm(request.POST)
        if form.is_valid() and form.cleaned_data['starttime'] < form.cleaned_data['endtime']:
            f = form.save(commit=False)
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
