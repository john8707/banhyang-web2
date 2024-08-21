from datetime import date, timedelta, datetime
from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from .models import Schedule, PracticeUser, Apply, WhyNotComing, SongData, Session
from banhyang.core.utils import weekday_dict


# Check user validation from PracticeUser model
def validate_user_exist(name, phonenumber):
    user = PracticeUser.objects.filter(username=name)
    if not user:
        return False
    else:
        return True


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
                     min_per_song=form_data['minutes'], starttime=form_data['starttime'], endtime=form_data['endtime'])
        s.save()


# 합주 신청 폼
class PracticeApplyForm(forms.Form):
    user_name = forms.CharField(label='이름')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                    'value': str(i.id) + "_-1"
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
                        'class': 'checkit'
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
        try:
            # 유저 이름 Validation
            user_object = PracticeUser.objects.get(username=form_data['user_name'])
            result['user_object'] = user_object
        except PracticeUser.DoesNotExist:
            raise ValidationError("이름을 다시 확인해주세요.")

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
            Apply.objects.filter(user_name=user_object, schedule_id=schedule_object).delete()
            WhyNotComing.objects.filter(user_name=user_object, schedule_id=schedule_object).delete()

            if reason_dict[schedule_object.id]:
                w = WhyNotComing(user_name=user_object, schedule_id=schedule_object, reason=reason_dict[schedule_object.id])
                w.save()

            apply_bulk_list = [Apply(user_name=user_object, schedule_id=schedule_object, not_available=x) for x in selected_dict[schedule_object.id]]
            Apply.objects.bulk_create(apply_bulk_list)


class SongSessionField(forms.CharField):
    """
    곡 데이터 추가 Form을 위한 커스텀 필드
    """
    def to_python(self, value):
        if not value:
            return []
        return value.split(',')


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
                user_objects = [PracticeUser.objects.get(username=x.strip()) for x in form_data[key] if x]
                form_data[key] = user_objects

            except PracticeUser.DoesNotExist:
                raise ValidationError("세션들의 이름을 다시 확인해주세요.")

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
            session_bulk_list = [Session(song_id=song_object, user_name=x, instrument=value) for x in form_data[key] if x]
            Session.objects.bulk_create(session_bulk_list)


class UserAddForm(forms.Form):
    """
    유저 추가 폼
    """
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': '이름'}))

    def clean(self):
        """
        등록하려는 유저의 이름이 이미 존재하는지 validate
        """
        form_data = self.cleaned_data
        try:
            user_exist = PracticeUser.objects.get(username=form_data['username'])
            if user_exist:
                raise ValidationError("해당 인원이 이미 존재합니다. 동명이인의 경우 숫자, 세션등을 이용해 구분하여 주세요.")
        except PracticeUser.DoesNotExist:
            return form_data

    def save(self) -> None:
        """
        유저 저장
        """
        user_name = self.cleaned_data['username']
        p = PracticeUser(username=user_name)
        p.save()
