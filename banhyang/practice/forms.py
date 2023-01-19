from django import forms
from .models import Schedule, SongData, PracticeUser
from django.core.exceptions import ValidationError

# Check user validation from PracticeUser model
def validate_user_exist(name, phonenumber):
    user = PracticeUser.objects.filter(username=name, phonenumber=phonenumber)
    if not user:
        return False
    else:
        return True

# 합주 날짜 생성 form -> Schedule model
class PracticeCreateForm(forms.ModelForm):
    # Schedule 모델 베이스 폼, field들 가져옴
    class Meta:
        model = Schedule
        fields = ['name', 'date', 'location']
    
    # 위에서 가져오지 않은 field들을 보기 편하게 만들어서 보여줌
    def __init__(self, *args, **kwargs):
        super(PracticeCreateForm, self).__init__(*args, **kwargs)
        self.fields['minutes'] = forms.ChoiceField(choices=[(6, "10분"), (3, "20분"), (2, "30분"), (1, "60분")])
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

# 곡 정보 추가 폼
class SongAddForm(forms.ModelForm):
    # SongData의 모델 베이스 폼. 모든 필드들 가져옴.
    class Meta:
        model = SongData
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SongAddForm, self).__init__(*args, **kwargs)
        # 아래의 필드들은 실제 저장될 때는 PracticeUser의 외래키로 저장되므로, TextInput으로 바꿔줌
        # View에서 save할때는 자동으로 외래키로 저장되는데, invalid 한 경우 특별한 메세지 없이 그냥 저장이 안됨.
        self.fields['vocal1'].widget = forms.TextInput()
        self.fields['vocal2'].widget = forms.TextInput()
        self.fields['drum'].widget = forms.TextInput()
        self.fields['guitar1'].widget = forms.TextInput()
        self.fields['guitar2'].widget = forms.TextInput()
        self.fields['bass'].widget = forms.TextInput()
        self.fields['keyboard1'].widget = forms.TextInput()
        self.fields['keyboard2'].widget = forms.TextInput()




# 바냥이들 정보 추가 폼
class UserAddForm(forms.ModelForm):
    class Meta:
        model= PracticeUser
        fields = '__all__'