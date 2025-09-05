# 표준 라이브러리
import typing

# Django Core
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login

# Project Apps
from .forms import LoginForm, SignupForm


# type alias when response is redirect or response
RedirectOrResponse = typing.Union[HttpResponse, HttpResponseRedirect]

def index(request):
    return render(request, 'index.html')

def new_index(request) -> HttpResponse:
    return render(request, 'new_index.html')

def new_login(request:HttpRequest) -> RedirectOrResponse:
    """
    로그인 페이지
    """
    # 로그인 되어있는 경우 불참 신청 페이지로 redirect
    if request.user.is_authenticated:
        return redirect('new_apply')

    form = LoginForm()
    # 로그인 하는 경우
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=raw_password)
            if user:
                auth_login(request, user)
                return redirect('new_apply')

    return render(request, 'new_login_signup.html', {'form' : form, 'title' : "LOGIN"})


def new_signup(request:HttpRequest) -> RedirectOrResponse:
    """
    회원가입 페이지
    """
    # 로그인 되어있는 경우 불참 신청 페이지로 redirect
    if request.user.is_authenticated:
        return redirect('new_apply')
    
    form = SignupForm()

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "회원가입 신청이 완료되었습니다. 임원진 승인 후 이용 가능합니다.")
            return redirect('new_index')

    return render(request, 'new_login_signup.html', {'form' : form, 'title' : "SIGN UP"})