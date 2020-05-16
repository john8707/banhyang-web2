from django import forms
from .models import Schedule, SongData, PracticeUser
from django.core.exceptions import ValidationError


def validate_user_exist(name, phonenumber):
    user = PracticeUser.objects.filter(username=name, phonenumber=phonenumber)
    if not user:
        return False
    else:
        return True

class PracticeCreateForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['name', 'date', 'location']
    
    def __init__(self, *args, **kwargs):
        super(PracticeCreateForm, self).__init__(*args, **kwargs)
        self.fields['minutes'] = forms.ChoiceField(choices=[(6, "10분"), (3, "20분"), (2, "30분")])
        self.fields['starttime'] = forms.TimeField(input_formats=['%H:%M'])
        self.fields['endtime'] = forms.TimeField(input_formats=['%H:%M'])


class PracticeApplyForm(forms.Form):
    username = forms.CharField(label="이름")
    number = forms.IntegerField(label="전화번호 뒷자리 4개")

    def clean(self):
        form_data = self.cleaned_data
        user = PracticeUser.objects.get(username=form_data['username'], phonenumber=form_data['number'])
        if not user:
            self._errors['username'] = ['이름과 전화번호를 다시 확인해주세요.']
        else:
            form_data['user_instance'] = user
        return form_data


class SongAddForm(forms.ModelForm):
    class Meta:
        model = SongData
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SongAddForm, self).__init__(*args, **kwargs)
        self.fields['vocal1'].widget = forms.TextInput()
        self.fields['vocal2'].widget = forms.TextInput()
        self.fields['guitar1'].widget = forms.TextInput()
        self.fields['guitar2'].widget = forms.TextInput()
        self.fields['bass'].widget = forms.TextInput()
        self.fields['keyboard1'].widget = forms.TextInput()
        self.fields['keyboard2'].widget = forms.TextInput()
        self.fields['drum'].widget = forms.TextInput()




class UserAddForm(forms.ModelForm):
    class Meta:
        model= PracticeUser
        fields = '__all__'