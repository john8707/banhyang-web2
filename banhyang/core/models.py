from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

#TODO : 기본 모델 (생성, 업데이트, 삭제 시간) 만들지 말지 결정하자

##Custom user models

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, name, email, phonenumber, gisu, password=None):

        if not email or not phonenumber or not gisu:
            raise ValueError('Must have valid information')
        user = self.model(
            username = username,
            name = name,
            email = self.normalize_email(email),
            phonenumber = phonenumber,
            gisu = gisu,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, name, email, phonenumber, gisu, password):
        user = self.create_user(
            username = username,
            name = name,
            email = self.normalize_email(email),
            phonenumber = phonenumber,
            gisu = gisu,
        )
        user.set_password(password)
        user.is_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    objects = UserManager()
    username = models.CharField(
        max_length=255,
        unique=True
    )
    name = models.CharField(
        max_length=255,
        unique=False
    )
    email = models.EmailField(
        max_length=255,
        unique=True
    )
    phonenumber = models.IntegerField()
    gisu = models.IntegerField()

    is_active = models.BooleanField(default=True)    
    is_admin = models.BooleanField(default=False)    
    is_superuser = models.BooleanField(default=False)    
    is_staff = models.BooleanField(default=False)     
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phonenumber', 'gisu', 'name']

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
    
##Practice models

class Schedule(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    date = models.DateTimeField()
    starttime = models.TimeField()
    endtime = models.TimeField()
    location = models.CharField(max_length=255,  null=True)
    div = models.IntegerField()
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return self.name + "(" + self.location + ")"


class Apply(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.CharField(max_length=255)
    schedule_id = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    not_available = models.IntegerField()


class SongData(models.Model):
    id = models.AutoField(primary_key=True)
    songname = models.CharField(max_length=255)
    vocal1 = models.CharField(max_length=255, null=True, blank=True)
    vocal2 = models.CharField(max_length=255, null=True, blank=True)
    guitar1 = models.CharField(max_length=255, null=True, blank=True)
    guitar2 = models.CharField(max_length=255, null=True, blank=True)
    bass = models.CharField(max_length=255, null=True, blank=True)
    keyboard1 = models.CharField(max_length=255, null=True, blank=True)
    keyboard2 = models.CharField(max_length=255, null=True, blank=True)
    drum = models.CharField(max_length=255, null=True, blank=True)