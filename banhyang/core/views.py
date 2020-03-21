from django.shortcuts import render, redirect
from django.http import HttpResponse
# Create your views here.

#통상적으로 HTML 문서와 같은 이름을 사용하자!!
def index(request):
    return render(request, 'index.html')
