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