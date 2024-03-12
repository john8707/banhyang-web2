from django import forms
from .models import Schedule, SongData, PracticeUser, Session, ArrivalTime
from django.core.exceptions import ValidationError
import datetime

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
        self.fields['starttime'] = forms.TimeField(input_formats=['%H:%M'], widget=forms.TimeInput(attrs={'type':'time'}))
        self.fields['endtime'] = forms.TimeField(input_formats=['%H:%M'], widget=forms.TimeInput(attrs={'type':'time'}))


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
    drums = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '드럼'}))
    guitars = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '기타'}))
    bass = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '베이스'}))
    keyboards = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder' : '키보드'}))

    etc = SongSessionField(required=False ,widget=forms.TextInput(attrs={'placeholder' : 'etc'}))

    def clean(self):
        form_data = self.cleaned_data
        try:
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
        #input한 이름의 유저가 존재하는지 validate
        try:
            user_exist = PracticeUser.objects.filter(username=form_data['username'])
            if user_exist:
                raise ValidationError("해당 인원이 이미 존재합니다. 동명이인의 경우 숫자, 세션등을 이용해 구분하여 주세요.")
        except PracticeUser.DoesNotExist:
            return form_data
        

class ArrivalAddForm(forms.Form):
    username = forms.CharField(required=True)

    def clean(self):
        form_data = self.cleaned_data

        #input한 이름의 유저가 존재하는지 validate
        try:
            user_exist = PracticeUser.objects.get(username=form_data['username'])
        except PracticeUser.DoesNotExist:
            raise ValidationError("해당 인원이 존재하지 않습니다. 오탈자를 다시 확인하거나 관리자에게 문의하세요.")
        
        #오늘 날짜 date + 0시0분0초 -> datetime 형식으로
        arrived_day_datetime = datetime.datetime.combine(datetime.date.today(), datetime.time(0,0,0,0,datetime.timezone.utc))

        #이미 인증을 했는지 validate
        arrival_exist = ArrivalTime.objects.filter(date=datetime.date.today(), user_name=user_exist)
        if arrival_exist:
            raise ValidationError("이미 도착 인증을 하였습니다. 도착시간 " + arrival_exist[0].arrival_time.strftime("%H:%M") )

        #오늘 합주가 존재하는지 validate
        schedule_exist = Schedule.objects.filter(date=arrived_day_datetime)
        if not schedule_exist:
            raise ValidationError("금일 예정된 합주가 없습니다. 날짜를 다시 확인하거나 관리자에게 문의하세요.")

        #합주 시작시간 30분 전이 됐는지 validate
        if schedule_exist.filter(starttime__lte = (datetime.datetime.now() + datetime.timedelta(minutes=30)).time()):
            #모든 validation 통과시 user object return
            return user_exist
        else:
            raise ValidationError("합주 시작 30분 전부터 도착 인증을 할 수 있습니다.")
        
