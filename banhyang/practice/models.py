from django.db import models

# 합주 날짜
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

# 바냥이들의 정보
class PracticeUser(models.Model):
    username = models.CharField(max_length=255,primary_key=True)
    gisu = models.IntegerField()
    phonenumber = models.IntegerField()

    def __str__(self):
        return self.username


# 개개인들의 불참 데이터
class Apply(models.Model):
    id = models.AutoField(primary_key=True)
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE)
    schedule_id = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='apply')
    not_available = models.IntegerField()


# 곡의 정보
class SongData(models.Model):
    id = models.AutoField(primary_key=True)
    songname = models.CharField(max_length=255)
    vocal1 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="vocal1")
    vocal2 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="vocal2")
    drum = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="drum")
    guitar1 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="guitar1")
    guitar2 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="guitar2")
    bass = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="bass")
    keyboard1 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="keyboard1")
    keyboard2 = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, null=True, blank=True, related_name="keyboard2")

    def __str__(self):
        return self.songname