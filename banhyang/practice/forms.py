from datetime import date, timedelta, datetime
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, ReadOnlyPasswordHashField, PasswordChangeForm

from .models import Schedule, Apply, WhyNotComing, SongData, Session, User
from banhyang.core.utils import weekday_dict

class AdminUserCreationForm(forms.ModelForm):
    """
    Admin page의 유저 생성 폼
    """
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2','name', 'email', 'student_id', 'phone_number', 'is_confirmed')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
    

class AdminUserChangeForm(forms.ModelForm):
    """
    Admin page의 유저 수정 폼
    """
    password = ReadOnlyPasswordHashField()
    class Meta:
        model = User
        fields = ('username','password', 'name', 'email', 'student_id', 'phone_number', 'is_confirmed')

    def clean_password(self):
        return self.initial["password"]


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
        

class UserModifyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = "이름"
        self.fields['name'].widget.attrs.update({'value': self.instance.name})

        self.fields['email'].label = "이메일"
        self.fields['email'].widget.attrs.update({'value': self.instance.email})

        self.fields['student_id'].label = "학번"
        self.fields['student_id'].widget.attrs.update({'value': self.instance.student_id})

        self.fields['phone_number'].label = "전화번호"
        self.fields['phone_number'].widget.attrs.update({'value': self.instance.phone_number})
    class Meta:
        model = get_user_model()
        fields = ('name', 'email', 'student_id', 'phone_number')


class PasswordModifyForm(PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
    
    class Meta:
        model = get_user_model()

class ScheduleCreateForm(forms.Form):
    """
    합주 날짜 생성 폼
    """
    name = forms.CharField(max_length=255, required=True)
    date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    location = forms.CharField(max_length=255, required=True)
    rooms = forms.IntegerField(required=True)
    minutes = forms.ChoiceField(choices=[(10, "10분"), (20, "20분"), (30, "30분"), (40, "40분"), (50, "50분"), (60, "60분")])
    starttime = forms.TimeField(input_formats=['%H:%M'], widget=forms.TimeInput(attrs={'type': 'time'}))
    endtime = forms.TimeField(input_formats=['%H:%M'], widget=forms.TimeInput(attrs={'type': 'time'}))

    def clean(self) -> dict:
        form_data = self.cleaned_data
        if form_data['starttime'] >= form_data['endtime']:
            raise ValidationError("합주의 시작 시간은 끝나는 시간 이전이어야 합니다.")
        return form_data

    def save(self) -> None:
        form_data = self.cleaned_data
        s = Schedule(name=form_data['name'], date=form_data['date'] + timedelta(hours=9), location=form_data['location'], rooms=form_data['rooms'],
                     min_per_song=form_data['minutes'], starttime=form_data['starttime'], endtime=form_data['endtime'], is_current=False)
        s.save()


# 합주 신청 폼
class PracticeApplyForm(forms.Form):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.user = user
        self.current_schedule = Schedule.objects.filter(is_current=True).order_by('date')
        self.generate_boolean_fields()

    # 동적으로 Boolean Field 생성
    def generate_boolean_fields(self):
        for i in self.current_schedule:
            time_counter = datetime.combine(date.today(), i.starttime)
            end_time = datetime.combine(date.today(), i.endtime)

            # 날짜 Display용 Fake input
            self.fields["label_" + str(i.id)] = forms.DateField(
                required=False,
                label="%s (%s~%s)" % (i.date.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(i.date.weekday()),
                                      i.starttime.strftime("%H:%M"),
                                      i.endtime.strftime("%H:%M")),
                widget=forms.DateInput(attrs={'display': 'None'}))

            # 불참 사유 input
            self.fields["why_not_coming_" + str(i.id)] = forms.CharField(max_length=255,
                                                                         required=False,
                                                                         label="불참 사유",
                                                                         widget=forms.TextInput(attrs={
                                                                             'class': 'why_not_coming'
                                                                         }))

            # 전체 참여 Checkbox
            self.fields["checkbox_" + str(i.id) + "_-1"] = forms.BooleanField(
                required=False,
                label="전체 참여",
                widget=forms.CheckboxInput(attrs={
                    'name': 'selected',
                    'value': str(i.id) + "_-1",
                    "onclick": "attendAll(this)"
                })
            )

            # 전체 불참 Checkbox
            self.fields["checkbox_" + str(i.id) + "_selectall"] = forms.BooleanField(
                required=False,
                label="전체 불참",
                widget=forms.CheckboxInput(attrs={
                    'name': 'selectall',
                    'value': 'selectall',
                    'onclick': 'selectAll(this)'
                })
            )

            # 각 합주에 맞게 동적인 Checkbox 생성
            division_counter = 0
            while time_counter < end_time:

                field_name = "checkbox_" + str(i.id) + "_" + str(division_counter)
                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label=time_counter.strftime("%H:%M"),
                    widget=forms.CheckboxInput(attrs={
                        'value': str(i.id) + "_" + str(division_counter),
                        'class': 'checkit',
                        'onclick': 'validateButtonChecked(this)'
                    })
                )
                time_counter += timedelta(minutes=10)
                division_counter += 1

    # Form Validation 진행
    def clean(self) -> dict:
        form_data = self.cleaned_data
        result = {}
        schedule_objects = Schedule.objects.filter(is_current=True).order_by('date')
        scheduleId_list = [x.id for x in schedule_objects]
        result['user_object'] = self.user


        selected_dict = {x: [] for x in scheduleId_list}
        reason_dict = {x: form_data['why_not_coming_' + str(x)] for x in scheduleId_list}
        for i, v in form_data.items():
            if 'checkbox' in i and v is True and 'selectall' not in i:
                res = i.split('_')
                selected_dict[int(res[1])].append(int(res[2]))

        for i in scheduleId_list:

            # Select At Least 1
            if selected_dict[i] == []:
                raise ValidationError("전체 참여 혹은 불참 시간을 각 날짜별로 선택해 주세요.")

            # Select either 전체 참여 or 불참
            elif -1 in selected_dict[i] and len(selected_dict[i]) > 1:
                raise ValidationError("불참 혹은 전체 참여 중 1가지만 선택해 주세요.")

            # Input reason if 불참
            elif reason_dict[i] == '' and -1 not in selected_dict[i]:
                raise ValidationError("불참 사유를 입력해 주세요.")

            # 전체 참여일시 Reason 지우기
            if -1 in selected_dict[i]:
                reason_dict[i] = ""

        result['selected_dict'] = selected_dict
        result['reason_dict'] = reason_dict
        result['schedule_objects'] = schedule_objects

        return result

    # 제출한 데이터 DB에 저장
    def save(self) -> None:
        form_data = self.cleaned_data
        user_object = form_data['user_object']
        selected_dict = form_data['selected_dict']
        reason_dict = form_data['reason_dict']
        schedule_objects = form_data['schedule_objects']

        for schedule_object in schedule_objects:
            Apply.objects.filter(user_id=user_object, schedule_id=schedule_object).delete()
            WhyNotComing.objects.filter(user_id=user_object, schedule_id=schedule_object).delete()

            if reason_dict[schedule_object.id]:
                w = WhyNotComing(user_id=user_object, schedule_id=schedule_object, reason=reason_dict[schedule_object.id])
                w.save()

            apply_bulk_list = [Apply(user_id=user_object, schedule_id=schedule_object, not_available=x) for x in selected_dict[schedule_object.id]]
            Apply.objects.bulk_create(apply_bulk_list)


class ApplyForm(forms.Form):
    """
    합주 불참 신청 form
    """
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.user = user
        self.current_schedule = Schedule.objects.filter(is_current=True).order_by('date')
        self.generate_boolean_fields()

    # 불참을 받을 합주 일정과 시간에 맞춰 동적으로 label, 불참 사유 input 및 check box 생성
    def generate_boolean_fields(self):
        for i in self.current_schedule:
            time_counter = datetime.combine(date.today(), i.starttime)
            end_time = datetime.combine(date.today(), i.endtime)

            # 날짜 Display용 Fake input
            self.fields["label_date" + str(i.id)] = forms.DateField(
                required=False,
                label="%s" % (i.date.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(i.date.weekday())))
            self.fields["label_time" + str(i.id)] = forms.TimeField(
                required=False,
                label="(%s~%s)" % (i.starttime.strftime("%H:%M"),
                                   i.endtime.strftime("%H:%M")))

            # 불참 사유 input
            self.fields["why_not_coming_" + str(i.id)] = forms.CharField(max_length=255,
                                                                         required=False,
                                                                         label="불참 사유",
                                                                         widget=forms.TextInput(attrs={
                                                                             'class': 'why_not_coming'
                                                                         }))

            # 전체 참여 Checkbox
            self.fields["checkbox_" + str(i.id) + "_-1"] = forms.BooleanField(
                required=False,
                label="전체 참여",
                widget=forms.CheckboxInput(attrs={
                    'name': 'selected',
                    'value': str(i.id) + "_-1",
                    "onclick": "attendAll(this)",
                    "style": "display: none;"
                })
            )

            # 전체 불참 Checkbox
            self.fields["checkbox_" + str(i.id) + "_selectall"] = forms.BooleanField(
                required=False,
                label="전체 불참",
                widget=forms.CheckboxInput(attrs={
                    'name': 'selectall',
                    'value': 'selectall',
                    'onclick': 'selectAll(this)',
                    "style": "display: none;"
                })
            )

            # 각 합주에 맞게 동적인 Checkbox 생성
            division_counter = 0
            while time_counter < end_time:

                field_name = "checkbox_" + str(i.id) + "_" + str(division_counter)
                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label=time_counter.strftime("%H:%M"),
                    widget=forms.CheckboxInput(attrs={
                        'value': str(i.id) + "_" + str(division_counter),
                        'class': 'checkit',
                        'onclick': 'validateButtonChecked(this)',
                        "style": "display: none;"
                    })
                )
                time_counter += timedelta(minutes=10)
                division_counter += 1
            
            self.fields['end' + str(i.id)] = forms.IntegerField(required=False)

    # Form Validation 진행
    def clean(self) -> dict:
        form_data = self.cleaned_data
        result = {}
        schedule_objects = Schedule.objects.filter(is_current=True).order_by('date')
        scheduleId_list = [x.id for x in schedule_objects]
        result['user_object'] = self.user


        selected_dict = {x: [] for x in scheduleId_list}
        reason_dict = {x: form_data['why_not_coming_' + str(x)] for x in scheduleId_list}
        for i, v in form_data.items():
            if 'checkbox' in i and v is True and 'selectall' not in i:
                res = i.split('_')
                selected_dict[int(res[1])].append(int(res[2]))

        for i in scheduleId_list:

            # Select At Least 1
            if selected_dict[i] == []:
                raise ValidationError("전체 참여 혹은 불참 시간을 각 날짜별로 선택해 주세요.")

            # Select either 전체 참여 or 불참
            elif -1 in selected_dict[i] and len(selected_dict[i]) > 1:
                raise ValidationError("불참 혹은 전체 참여 중 1가지만 선택해 주세요.")

            # Input reason if 불참
            elif reason_dict[i] == '' and -1 not in selected_dict[i]:
                raise ValidationError("불참 사유를 입력해 주세요.")

            # 전체 참여일시 Reason 지우기
            if -1 in selected_dict[i]:
                reason_dict[i] = ""

        result['selected_dict'] = selected_dict
        result['reason_dict'] = reason_dict
        result['schedule_objects'] = schedule_objects

        return result

    # 제출한 데이터 DB에 저장
    def save(self) -> None:
        form_data = self.cleaned_data
        user_object = form_data['user_object']
        selected_dict = form_data['selected_dict']
        reason_dict = form_data['reason_dict']
        schedule_objects = form_data['schedule_objects']

        for schedule_object in schedule_objects:
            Apply.objects.filter(user_id=user_object, schedule_id=schedule_object).delete()
            WhyNotComing.objects.filter(user_id=user_object, schedule_id=schedule_object).delete()

            if reason_dict[schedule_object.id]:
                w = WhyNotComing(user_id=user_object, schedule_id=schedule_object, reason=reason_dict[schedule_object.id])
                w.save()

            apply_bulk_list = [Apply(user_id=user_object, schedule_id=schedule_object, not_available=x) for x in selected_dict[schedule_object.id]]
            Apply.objects.bulk_create(apply_bulk_list)



class SongSessionField(forms.CharField):
    """
    곡 데이터 추가 Form을 위한 커스텀 필드
    """
    def to_python(self, value):
        """
        입력된 문자열을 쉼표(,)로 분리하여 리스트로 변환
        """
        if not value:
            return []
        return [v for v in (item.strip() for item in value.split(',')) if v]

    def clean(self, value):
        """
        유저 존재 여부를 validate한 후 user를 모델 objects로 변경 후 리턴
        """
        name_list = super().clean(value)
        if not name_list:
            return []
        
        user_objects = []
        not_found_users = []
        names = [name.strip() for name in name_list if name.strip()]
        users = User.objects.filter(name__in=names)
        user_dict = {user.name: user for user in users}
        for name in names:
            if name in user_dict:
                user_objects.append(user_dict[name])
            else:
                not_found_users.append(name)
        
        if not_found_users:
            raise ValidationError(f"일치하는 이름을 찾을 수 없습니다: {', '.join(not_found_users)}")
        return user_objects
    
class NewSongAddForm(forms.Form):
    """
    곡 데이터 추가 폼
    """
    title = forms.CharField(required=False, widget=forms.TextInput())
    vocals = SongSessionField(required=False, widget=forms.TextInput())
    drums = SongSessionField(required=False, widget=forms.TextInput())
    guitars = SongSessionField(required=False, widget=forms.TextInput())
    bass = SongSessionField(required=False, widget=forms.TextInput())
    keyboards = SongSessionField(required=False, widget=forms.TextInput())
    etc = SongSessionField(required=False, widget=forms.TextInput())

    def clean(self) -> dict:
        """
        title이 비어있는데 세션에 값이 있는 경우 에러 처리
        """
        cleaned_data = super().clean()

        # title이 비어있는데 세션에 값이 있는 경우 에러 처리
        if any(cleaned_data.values()):
            if not cleaned_data.get('title'):
                self.add_error('title', "곡 제목을 입력해 주세요.")

        return cleaned_data
    
    def save(self) -> None:
        """
        Custom Save for NewSongAddForm.
        이미 동명의 곡이 존재하는 경우 SongData에서 삭제 후 SongData, Session 데이터 저장
        """
        form_data = self.cleaned_data
        if not form_data.get('title'):
            return  # title이 비어있으면 저장하지 않음

        song_exist = SongData.objects.filter(songname=form_data['title']).prefetch_related('session')
        # 기존 곡이 존재하면 해당 곡의 세션 데이터 삭제
        if song_exist:
            for i in song_exist:
                song_object = i
                i.session.all().delete()
        # 기존 곡이 존재하지 않으면 새로 생성
        else:
            song_object = SongData(songname=form_data['title'])
            song_object.save()

        session_index = {'vocals': 'v', 'drums': 'd', 'guitars': 'g', 'bass': 'b', 'keyboards': 'k', 'etc': 'etc'}

        # 세션 데이터 bulk create
        for key, value in session_index.items():
            session_bulk_list = [Session(song_id=song_object, user_id=x, instrument=value) for x in form_data[key] if x]
            Session.objects.bulk_create(session_bulk_list)


class SongAddForm(forms.Form):
    """
    곡 데이터 추가 폼
    """
    song_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': '곡 제목'}))
    vocals = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder': '보컬'}))
    drums = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder': '드럼'}))
    guitars = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder': '기타'}))
    bass = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder': '베이스'}))
    keyboards = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder': '키보드'}))

    etc = SongSessionField(required=False, widget=forms.TextInput(attrs={'placeholder': 'etc'}))

    def session_index(self) -> dict:
        """
        key : 세션의 명칭, value : 축약어 형태의 dictionary 리턴
        ex) {'vocals': 'v', 'drums': 'd', 'guitars': 'g', 'bass': 'b', 'keyboards': 'k', 'etc': 'etc'}
        """
        index = {'vocals': 'v', 'drums': 'd', 'guitars': 'g', 'bass': 'b', 'keyboards': 'k', 'etc': 'etc'}
        return index
    
    def clean(self) -> dict:
        """
        유저 존재 여부를 validate한 후 user를 모델 objects로 변경 후 리턴
        """
        form_data = self.cleaned_data
        for key in self.session_index():
            try:
                user_objects = []
                for x in form_data[key]:
                    if x:
                        user_objects.append(User.objects.get(name=x.strip()))
                form_data[key] = user_objects

            except User.DoesNotExist:
                raise ValidationError("일치하는 이름을 찾을 수 없습니다 :" + x)


        return form_data
    
    def save(self) -> None:
        """
        Custom Save for SongAddForm.
        이미 동명의 곡이 존재하는 경우 SongData에서 삭제 후 SongData, Session 데이터 저장
        """
        form_data = self.cleaned_data
        song_exist = SongData.objects.filter(songname=form_data['song_name'])

        if song_exist:
            for i in song_exist:
                song_object = i
                i.session.all().delete()

        else:
            song_object = SongData(songname=form_data['song_name'])
            song_object.save()

        for key, value in self.session_index().items():
            session_bulk_list = [Session(song_id=song_object, user_id=x, instrument=value) for x in form_data[key] if x]
            Session.objects.bulk_create(session_bulk_list)
