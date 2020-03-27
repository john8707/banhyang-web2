from django import forms
from .models import AccountingTitle, AccountingDetails, Schedule

class AccountingCreateForm(forms.ModelForm):
    class Meta:
        model = AccountingTitle
        fields = ['title', 'description'] 

        widgets = {
            'title' : forms.TextInput(attrs={'placeholder' : 'ex) 2020 여름 정기공연'}),
            'description' : forms.Textarea(attrs={'placeholder' : 'ex) 6월 12일 @라이브와이어'})
        }

class AccountingAddForm(forms.ModelForm):
    class Meta:
        model = AccountingDetails
        fields = ['date', 'value', 'note', 'remark']

class ConcertCreateForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['name', 'date', 'location']
    
    def __init__(self, *args, **kwargs):
        super(ConcertCreateForm, self).__init__(*args, **kwargs)
        self.fields['minutes'] = forms.ChoiceField(choices=[(6, "10분"), (3, "20분"), (2, "30분")])
        self.fields['starttime'] = forms.TimeField(input_formats=['%H:%M'])
        self.fields['starttime'].widget.attrs['placeholder'] = "시간:분 형식(ex 7:30)"
        self.fields['endtime'] = forms.TimeField(input_formats=['%H:%M'])
        self.fields['endtime'].widget.attrs['placeholder'] = "시간:분 형식(ex 7:30)"