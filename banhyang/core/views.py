from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .forms import AccountingCreateForm, AccountingAddForm, ConcertCreateForm
from django.views.decorators.csrf import csrf_exempt
from .models import AccountingTitle, AccountingDetails, Schedule 
from django.db.models import Sum
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

def concert_create(request):
    
    if request.method == "POST":
        form = ConcertCreateForm(request)
        if form.is_valid():
            f = form.save(commit=False)
            f.div = form.minutes
            f.save()
            return redirect('index')
    else:
        form = ConcertCreateForm()

    return render(request, 'concert_create.html', {'form' : form})