from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .forms import CreateForm, AddForm
from django.views.decorators.csrf import csrf_exempt
from .models import AccountingTitle, AccountingDetails
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
        form = CreateForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.save()
            return redirect('accounting_main')
        
    else:
        form = CreateForm()
        return render(request, 'accounting_create.html', {'form' : form,})

def accounting_details(request, id):
    info = get_object_or_404(AccountingTitle, id=id)
    accounting_list = AccountingDetails.objects.filter(accounting_id=id).order_by('date')
    accounting_sum = accounting_list.aggregate(Sum('value'))

    if request.method == "POST":
        form = AddForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.accounting_id = info
            f.save()
            return redirect('accounting_details', id=id)
    else:
        form = AddForm()
    return render(request, 'accounting_details.html', {'accounting_list' : accounting_list, 'info' : info, 'sum' : accounting_sum, 'form' : form
    })

def accounting_details_delete(request, accounting_id, detail_id):
    detail_to_delete = get_object_or_404(AccountingDetails, id = detail_id)
    detail_to_delete.delete()
    return redirect('accounting_details', id=accounting_id)