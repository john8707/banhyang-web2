from django import forms
from .models import Schedule, SongData, PracticeUser, Session
from django.core.exceptions import ValidationError

# Check user validation from PracticeUser model
def validate_user_exist(name, phonenumber):
    user = PracticeUser.objects.filter(username=name)
    if not user:
        return False
    else:
        return True

# 합주 날짜 생성 form -> Schedule model
class PracticeCreateForm(forms.ModelForm):
    # Schedule 모델 베이스 폼, field들 가져옴
    class Meta:
        model = Schedule
        fields = ['name', 'date', 'location', 'rooms']
    
    # 위에서 가져오지 않은 field들을 보기 편하게 만들어서 보여줌
    def __init__(self, *args, **kwargs):
        super(PracticeCreateForm, self).__init__(*args, **kwargs)
        self.fields['minutes'] = forms.ChoiceField(choices=[(10, "10분"), (20, "20분"), (30, "30분"), (40, "40분"), (50, "50분"), (60, "60분")])
        self.fields['starttime'] = forms.TimeField(input_formats=['%H:%M'])
        self.fields['endtime'] = forms.TimeField(input_formats=['%H:%M'])


# 합주 신청 폼
class PracticeApplyForm(forms.Form):
    username = forms.CharField(label="이름")

    # form의 username이 valid 한지 확인
    def clean(self):
        form_data = self.cleaned_data
        try:
            # valid 한 경우 PracticeUser의 object를 form_data에 넣어서 리턴
            user = PracticeUser.objects.get(username=form_data['username'])
            form_data['user_object'] = user
        except PracticeUser.DoesNotExist:
            # invalid 한 경우 에러 메세지 리턴
            self._errors['message'] = '이름을 다시 확인해주세요.'

        return form_data


# 곡 세션 추가 전용 커스텀 필드
class SongSessionField(forms.CharField):
    def to_python(self, value):
        if not value:
            return []
        return value.split(',')


# 곡 제목 추가 폼
class SongAddForm(forms.Form):
    song_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder' : '곡 제목'}))
    vocals = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '보컬'}))
    guitars = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '기타'}))
    bass = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '베이스'}))
    keyboards = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '키보드'}))
    drums = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '드럼'}))

    etc = SongSessionField(required=False ,widget=forms.TextInput(attrs={'placeholder' : 'etc'}))

    def clean(self):
        form_data = self.cleaned_data
        try:
            song_exist = SongData.objects.filter(songname=form_data['song_name'])
            if song_exist:
                raise ValidationError('해당 곡이 이미 존재합니다.')
            
            for key,values in form_data.items():
                if key != "song_name" and values:
                    user_objects = [PracticeUser.objects.get(username=x.strip()) for x in values if x]
                    form_data[key] = user_objects

        except PracticeUser.DoesNotExist:
                raise ValidationError('세션들의 이름을 다시 확인해주세요.')
        return form_data


# 바냥이들 정보 추가 폼
class UserAddForm(forms.Form):
    
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder' : '이름'}))
    
    def clean(self):
        form_data = self.cleaned_data
        try:
            user_exist = PracticeUser.objects.filter(username=form_data['username'])
            if user_exist:
                raise ValidationError("해당 인원이 이미 존재합니다. 동명이인의 경우 숫자, 세션등을 이용해 구분하여 주세요.")
        except PracticeUser.DoesNotExist:
            return form_data
        
