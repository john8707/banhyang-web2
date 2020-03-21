from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import CreateForm
from django.views.decorators.csrf import csrf_exempt
# Create your views here.

#통상적으로 HTML 문서와 같은 이름을 사용하자!!
def index(request):
    return render(request, 'index.html')

def accounting_main(request):
    return render(request, 'accounting_main.html')

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
