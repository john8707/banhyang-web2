from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .forms import AccountingCreateForm, AccountingAddForm, ConcertCreateForm, ConcertApplyForm
from django.views.decorators.csrf import csrf_exempt
from .models import AccountingTitle, AccountingDetails, Schedule 
from django.db.models import Sum
from datetime import timedelta, date, datetime, time
# Create your views here.

#통상적으로 HTML 문서와 같은 이름을 사용하자!!
def index(request):
    return render(request, 'index.html')

def accounting_main(request):
    accounting_list = AccountingTitle.objects.all()

    return render(request, 'accounting_main.html', {'accounting_list' : accounting_list,})

#deactivating csrf token
@csrf_exempt
def accounting_create(request):
    
    if request.method == "POST":
        form = AccountingCreateForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.save()
            return redirect('accounting_main')
        
    else:
        form = AccountingCreateForm()
        return render(request, 'accounting_create.html', {'form' : form,})

def accounting_details(request, id):
    info = get_object_or_404(AccountingTitle, id=id)
    accounting_list = AccountingDetails.objects.filter(accounting_id=id).order_by('date')
    accounting_sum = accounting_list.aggregate(Sum('value'))

    if request.method == "POST":
        form = AccountingAddForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.accounting_id = info
            f.save()
            return redirect('accounting_details', id=id)
    else:
        form = AccountingAddForm()
    return render(request, 'accounting_details.html', {'accounting_list' : accounting_list, 'info' : info, 'sum' : accounting_sum, 'form' : form
    })

def accounting_details_delete(request, accounting_id, detail_id):
    detail_to_delete = get_object_or_404(AccountingDetails, id = detail_id)
    detail_to_delete.delete()
    return redirect('accounting_details', id=accounting_id)

##TODO 눈에 보이고자 하는 날짜 선택하기 -> 유저가 선택해서 업로드 -> 관리자가 전체를 볼 수 있게하자
### + 마감 기능, 보이는 날짜 바꾸기
### 한번 생성 시 계산 한 번 한 후 DB에 저장하자. 매번 하면 개느릴 것 같음

def concert(request):

    return render(request, 'concert.html')

def concert_create(request):
    #TODO 어떻게 추가하는지 써놓기(시간은 가능한 한 시간 or 삼십분 단위로 할 것, )
    if request.method == "POST":
        form = ConcertCreateForm(request.POST)
        if form.is_valid() and form.cleaned_data['starttime'] < form.cleaned_data['endtime']:
            f = form.save(commit=False)
            f.div = form.cleaned_data['minutes']
            f.starttime = form.cleaned_data['starttime']
            f.endtime = form.cleaned_data['endtime']
            f.save()
            return redirect('concert')
    else:
        form = ConcertCreateForm()

    return render(request, 'concert_create.html', {'form' : form})

def concert_apply(request):
    #불참 타임
    if request.method == "POST":
        form = ConcertApplyForm(request.POST)
    else:
        current_concert = Schedule.objects.filter(is_current=False)
        res = {}
        choice = []
        for i in current_concert:
            temp = {}
            temp['name'] = i.name
            temp['date'] = i.date
            temp['time_list'] = []
            temp_time = datetime.combine(date.today(), i.starttime)
            endtime = datetime.combine(date.today(), i.endtime)
            time_per_song = 60 / i.div
            div_day = 0
            while  temp_time + timedelta(minutes=time_per_song) < endtime:
                if div_day == 0:
                    choice.append(((i.id, div_day),"%s - %s, (%s)"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"), temp['date'].strftime('%m/%d'))))
                else:
                    choice.append(((i.id, div_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"))))
                temp_time += timedelta(minutes=time_per_song)
                div_day += 1

            choice.append(((i.id, div_day),"%s - %s"%(temp_time.strftime("%H:%M"), (temp_time + timedelta(minutes=time_per_song)).strftime("%H:%M"))))

            res[i.id] = temp
        form = ConcertApplyForm(choices=choice)
        
    return render(request, 'concert_apply.html', {'form' : form})