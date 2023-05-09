from django.db import models

# 합주 날짜
class Schedule(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    date = models.DateTimeField()
    starttime = models.TimeField()
    endtime = models.TimeField()
    location = models.CharField(max_length=255,  null=True)
    min_per_song = models.IntegerField()
    is_current = models.BooleanField(default=True)
    rooms = models.IntegerField()

    def __str__(self):
        return f"{self.date.strftime('%y/%m/%d(%a)')} - {self.starttime.strftime('%H:%M')}~{self.endtime.strftime('%H:%M')} - 곡 당 {self.min_per_song}분"


# 바냥이들의 정보
class PracticeUser(models.Model):
    username = models.CharField(max_length=255,primary_key=True)

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
    def __str__(self):
        return self.songname


# 곡의 세션이 누구인지 곡id(fk),이름(fk),세션 정보(v,d,g,k,b 등으로 표기하자)
class Session(models.Model):
    id = models.AutoField(primary_key=True)
    song_id = models.ForeignKey(SongData, on_delete=models.CASCADE, related_name='session')
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE)
    instrument = models.CharField(max_length=255)
    def __str__(self) -> str:
        return ",".join([self.song_id.songname, self.user_name.username, self.instrument])