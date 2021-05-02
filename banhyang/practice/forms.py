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
        self.fields['minutes'] = forms.ChoiceField(choices=[(6, "10분"), (3, "20분"), (2, "30분"), (1, "60분")])
        self.fields['starttime'] = forms.TimeField(input_formats=['%H:%M'])
        self.fields['endtime'] = forms.TimeField(input_formats=['%H:%M'])


class PracticeApplyForm(forms.Form):
    username = forms.CharField(label="이름")

    def clean(self):
        form_data = self.cleaned_data
        try:
            user = PracticeUser.objects.get(username=form_data['username'])
            form_data['user_object'] = user
        except PracticeUser.DoesNotExist:
            self._errors['number'] = ['이름을 다시 확인해주세요.']

        return form_data


class SongAddForm(forms.ModelForm):
    class Meta:
        model = SongData
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SongAddForm, self).__init__(*args, **kwargs)
        self.fields['vocal1'].widget = forms.TextInput()
        self.fields['vocal2'].widget = forms.TextInput()
        self.fields['drum'].widget = forms.TextInput()
        self.fields['guitar1'].widget = forms.TextInput()
        self.fields['guitar2'].widget = forms.TextInput()
        self.fields['bass'].widget = forms.TextInput()
        self.fields['keyboard1'].widget = forms.TextInput()
        self.fields['keyboard2'].widget = forms.TextInput()




class UserAddForm(forms.ModelForm):
    class Meta:
        model= PracticeUser
        fields = '__all__'