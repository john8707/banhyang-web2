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
    minutes = forms.ChoiceField(choices=[(6, "10분"), (3, "20분"), (2, "30분")])
    class Meta:
        model = Schedule
        fields = ['name', 'starttime', 'endtime', 'location']
