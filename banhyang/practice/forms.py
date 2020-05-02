from django import forms
from .models import Schedule, SongData

class PracticeCreateForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['name', 'date', 'location']
    
    def __init__(self, *args, **kwargs):
        super(PracticeCreateForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['placeholder'] = "ex 정기합주"
        self.fields['minutes'] = forms.ChoiceField(choices=[(6, "10분"), (3, "20분"), (2, "30분")])
        self.fields['starttime'] = forms.TimeField(input_formats=['%H:%M'])
        self.fields['starttime'].widget.attrs['placeholder'] = "시간:분 형식(ex 7:00)"
        self.fields['endtime'] = forms.TimeField(input_formats=['%H:%M'])
        self.fields['endtime'].widget.attrs['placeholder'] = "시간:분 형식(ex 8:00)"


class PracticeApplyForm(forms.Form):
    def __init__(self, choices=(), *args, **kwargs):
        super(PracticeApplyForm, self).__init__(*args, **kwargs)
        self.fields['not_available'].choices = choices


    username = forms.CharField(label="이름")
    #TODO : 이름, 전화번호, 활동기수인지 validate
    number = forms.IntegerField(label="전화번호 뒷자리 4개")
    not_available = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, label="불가능한 시간을 선택해주세요.")


class SongAddForm(forms.ModelForm):
    class Meta:
        model = SongData
        fields = '__all__'