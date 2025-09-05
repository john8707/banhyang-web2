from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'id': "login_username"}),
                               label="아이디")
    password = forms.CharField(widget=forms.PasswordInput(),
                               label="비밀번호")
    
    def clean(self):
        form_data = self.cleaned_data
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=form_data.get('username'))
            check_password = user.check_password(form_data.get('password'))
            is_confirmed = user.is_confirmed
            if not check_password:
                self.add_error("password", ValidationError("비밀번호가 일치하지 않습니다."))
            
            elif not is_confirmed:
                self.add_error(None, ValidationError("승인되지 않은 사용자입니다. 관리자에게 문의하세요."))

        except user_model.DoesNotExist:
            self.add_error("username", ValidationError("아이디가 존재하지 않습니다."))


class SignupForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "아이디"
        self.fields['username'].widget.attrs.update({'placeholder': "영/숫자 4~12자리",
                                                     'id' : "signup_username"})

        self.fields['password1'].label = "비밀번호"
        self.fields['password1'].help_text = None
        self.fields['password1'].widget.attrs.update({'placeholder': "8자리 이상"})

        self.fields['password2'].label = "비밀번호 확인"
        self.fields['password2'].help_text = None
        self.fields['password2'].widget.attrs.update({'placeholder': "8자리 이상"})

        self.fields['name'].label = "이름"
        self.fields['name'].widget.attrs.update({'placeholder': "김반향"})

        self.fields['email'].label = "이메일"
        self.fields['email'].widget.attrs.update({'placeholder': "banhyang@yonsei.ac.kr"})

        self.fields['student_id'].label = "학번"
        self.fields['student_id'].widget.attrs.update({'placeholder': "2018000000"})

        self.fields['phone_number'].label = "전화번호"
        self.fields['phone_number'].widget.attrs.update({'placeholder': "01012345678"})

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class' : 'signup_form'
            })

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if "-" in phone_number:
            phone_number = phone_number.replace("-","")
        return phone_number

    class Meta:
        model = get_user_model()
        fields = ('username', 'password1', 'password2','name', 'email', 'student_id', 'phone_number')
        help_texts = {
            'username' : None
        }