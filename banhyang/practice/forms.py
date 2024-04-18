from django import forms
from .models import Schedule, PracticeUser, Apply, WhyNotComing
from django.core.exceptions import ValidationError
import datetime
from datetime import date
from banhyang.core.utils import weekday_dict

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
    user_name = forms.CharField(label='이름')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_schedule = Schedule.objects.filter(is_current=True).order_by('date')
        self.generate_boolean_fields()


    # 동적으로 Boolean Field 생성
    def generate_boolean_fields(self):
        for i in self.current_schedule:
            time_counter = datetime.datetime.combine(date.today(), i.starttime)
            end_time = datetime.datetime.combine(date.today(), i.endtime)

            # 날짜 Display용 Fake input
            self.fields["label_" + str(i.id)] = forms.DateField(
                required=False,
                label="%s (%s~%s)"%(i.date.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') +weekday_dict(i.date.weekday()),
                                    i. starttime.strftime("%H:%M"),
                                    i.endtime.strftime("%H:%M")),
                widget=forms.DateInput(attrs={'display':'None'}))
            
            # 불참 사유 input
            self.fields["why_not_coming_" + str(i.id)] = forms.CharField(max_length=255, 
                                                                         required=False, 
                                                                         label="불참 사유",
                                                                         widget=forms.TextInput(attrs={
                                                                             'class' : 'why_not_coming'
                                                                         }))

            # 전체 참여 Checkbox
            self.fields["checkbox_" + str(i.id) +"_-1"] = forms.BooleanField(
                required=False,
                label="전체 참여",
                widget=forms.CheckboxInput(attrs={
                    'name' : 'selected',
                    'value' : str(i.id) + "_-1"
                })
            )

            # 전체 불참 Checkbox
            self.fields["checkbox_" + str(i.id) + "_selectall"] = forms.BooleanField(
                required=False,
                label="전체 불참",
                widget=forms.CheckboxInput(attrs={
                    'name' : 'selectall',
                    'value' : 'selectall',
                    'onclick' : 'selectAll(this)'
                })
            )
            

            # 각 합주에 맞게 동적인 Checkbox 생성
            division_counter = 0
            while time_counter < end_time:

                field_name = "checkbox_" + str(i.id) + "_" +  str(division_counter)
                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label = time_counter.strftime("%H:%M"),
                    widget=forms.CheckboxInput(attrs={
                        'value' : str(i.id) + "_" +  str(division_counter),
                        'class' : 'checkit'
                    })
                )
                time_counter += datetime.timedelta(minutes=10)
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
        
        selected_dict = {x:[] for x in scheduleId_list}
        reason_dict = {x: form_data['why_not_coming_'+ str(x)] for x in scheduleId_list}
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
        data = self.cleaned_data
        user_object = data['user_object']
        selected_dict = data['selected_dict']
        reason_dict = data['reason_dict']
        schedule_objects = data['schedule_objects']
        for schedule_object in schedule_objects:
            Apply.objects.filter(user_name=user_object,schedule_id=schedule_object).delete()
            WhyNotComing.objects.filter(user_name=user_object,schedule_id=schedule_object).delete()

            if reason_dict[schedule_object.id]:
                w = WhyNotComing(user_name=user_object, schedule_id=schedule_object, reason=reason_dict[schedule_object.id])
                w.save()
            
            apply_bulk_list=[Apply(user_name=user_object, schedule_id=schedule_object, not_available=x) for x in selected_dict[schedule_object.id]]
            Apply.objects.bulk_create(apply_bulk_list)



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