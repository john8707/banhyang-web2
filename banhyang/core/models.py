from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

#TODO : 기본 모델 (생성, 업데이트, 삭제 시간) 만들지 말지 결정하자


##accounting models

class AccountingTitle(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.title

class AccountingDetails(models.Model):
    id = models.AutoField(primary_key=True)
    accounting_id = models.ForeignKey(AccountingTitle, on_delete=models.CASCADE)
    date = models.DateField()
    value = models.IntegerField()
    note = models.TextField()
    remark = models.TextField(null=True)
    
    def __str__(self):
        return self.title + self.note
    
