from django import forms
from .models import AccountingTitle, AccountingDetails

class CreateForm(forms.ModelForm):
    class Meta:
        model = AccountingTitle
        fields = ['title', 'description'] 

        widgets = {
            'title' : forms.TextInput(attrs={'placeholder' : 'ex) 2020 여름 정기공연'}),
            'description' : forms.Textarea(attrs={'placeholder' : 'ex) 6월 12일 @라이브와이어'})
        }

class AddForm(forms.ModelForm):
    class Meta:
        model = AccountingDetails
        fields = ['date', 'value', 'note', 'remark']