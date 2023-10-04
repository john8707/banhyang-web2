from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
# Create your views here.

#통상적으로 HTML 문서와 같은 이름을 사용하자!!
def index(request):
    return render(request, 'index.html')
