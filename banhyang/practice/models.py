from django.db import models

# Create your models here.
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
        return self.name + "(" + self.date.strftime("%m/%d") + ")"


class PracticeUser(models.Model):
    username = models.CharField(max_length=255,primary_key=True)
    gisu = models.IntegerField()
    phonenumber = models.IntegerField()

    def __str__(self):
        return self.username


class Apply(models.Model):
    id = models.AutoField(primary_key=True)
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE)
    schedule_id = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    not_available = models.IntegerField()


class SongData(models.Model):
    id = models.AutoField(primary_key=True)
    songname = models.CharField(max_length=255)
    vocal1 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="vocal1")
    vocal2 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="vocal2")
    guitar1 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="guitar1")
    guitar2 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="guitar2")
    bass = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="bass")
    keyboard1 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="keyboard1")
    keyboard2 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="keyboard2")
    drum = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="drum")
