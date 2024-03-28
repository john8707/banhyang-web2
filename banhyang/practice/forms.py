from django import forms
from .models import Schedule, SongData, PracticeUser, Session, Timetable, AttendanceCheck
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
class ScheduleCreateForm(forms.ModelForm):
    # Schedule 모델 베이스 폼, field들 가져옴
    class Meta:
        model = Schedule
        fields = ['name', 'date', 'location', 'rooms']
    
    # 위에서 가져오지 않은 field들을 보기 편하게 만들어서 보여줌
    def __init__(self, *args, **kwargs):
        super(ScheduleCreateForm, self).__init__(*args, **kwargs)
        self.fields['minutes'] = forms.ChoiceField(choices=[(10, "10분"), (20, "20분"), (30, "30분"), (40, "40분"), (50, "50분"), (60, "60분")])
        self.fields['starttime'] = forms.TimeField(input_formats=['%H:%M'], widget=forms.TimeInput(attrs={'type':'time'}))
        self.fields['endtime'] = forms.TimeField(input_formats=['%H:%M'], widget=forms.TimeInput(attrs={'type':'time'}))


# 합주 신청 폼
class PracticeApplyForm(forms.Form):
    user_name = forms.CharField(label="이름")

    def clean(self):
        form_data = self.cleaned_data
        user_name = form_data['user_name']
        # 유저의 이름이 DB에 저장되어있는지 Validate
        try:
            user_object = PracticeUser.objects.get(username=user_name)
            form_data['user_object'] = user_object
        except PracticeUser.DoesNotExist:
            raise ValidationError("이름을 다시 확인해주세요.")

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
        

class AttendanceCheckForm(forms.Form):
    username = forms.CharField(required=True)

    def clean(self):
        form_data = self.cleaned_data

        now = datetime.datetime.now()

        #input한 이름의 유저가 존재하는지 validate
        try:
            user_exist = PracticeUser.objects.get(username=form_data['username'])
        except PracticeUser.DoesNotExist:
            raise ValidationError("해당 인원이 존재하지 않습니다. 오탈자를 다시 확인하거나 관리자에게 문의하세요.")
        
        #오늘 날짜 date + 0시0분0초 -> datetime 형식으로
        arrived_day_datetime = datetime.datetime.combine(datetime.date.today(), datetime.time(0,0,0,0,datetime.timezone.utc))

        #오늘 합주가 존재하는지 validate
        schedule_exist = Schedule.objects.filter(date=arrived_day_datetime)
        if not schedule_exist:
            raise ValidationError("금일 예정된 합주가 없습니다. 날짜를 다시 확인하거나 관리자에게 문의하세요.")
        
        #저장된 합주 시간표가 있는지 validate
        timetable_exist = Timetable.objects.filter(schedule_id__in=schedule_exist)
        if not timetable_exist:
            raise ValidationError("데이터베이스에 저장된 시간표가 존재하지 않습니다. 관리자에게 문의하세요.")

        #현재 인증가능한 합주가 있는지
        song_now = timetable_exist.filter(start_time__lte = (now + datetime.timedelta(minutes=4)).time(), end_time__gt=(now + datetime.timedelta(minutes=4)).time())
        if not song_now:
            raise ValidationError("현재 출석 체크 가능한 곡이 존재하지 않습니다. 합주 시작 4분전 ~ 종료 4분전까지 인증 가능합니다.")
        


        #현재 진행중인 곡이 내가 참여하는 곡인지
        do_i_play_list=[]
        for i in song_now:
            do_i_play = i.song_id.session.filter(user_name=user_exist)
            if do_i_play:
                do_i_play_list.append(i)
        
        if not do_i_play_list:
            raise ValidationError("현재 출석 체크 가능한 곡 중 연주하는 곡이 없습니다. 합주 시작 4분전 ~ 종료 4분전까지 인증 가능합니다.")
        
        attendance_exist = AttendanceCheck.objects.filter(timetable_id__in=do_i_play_list, user_name=user_exist)
        if attendance_exist:
            raise ValidationError("이미 인증이 완료되었습니다. 합주 시작 4분전 ~ 종료 4분전까지 인증 가능합니다.")
        

        return user_exist, do_i_play_list, now