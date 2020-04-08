from django.db import models
# Create your models here.

#TODO : 기본 모델 (생성, 업데이트, 삭제 시간) 만들지 말지 결정하자

##User models

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

class Schedule(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    date = models.DateTimeField()
    starttime = models.TimeField()
    endtime = models.TimeField()
    location = models.CharField(max_length=255,  null=True)
    div = models.IntegerField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.name + "(" + self.location + ")"

class Apply(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.CharField(max_length=255)
    schedule_id = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    not_available = models.IntegerField()