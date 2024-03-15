from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

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
        return f"{self.date.strftime('%y/%m/%d(%a)')}/{self.starttime.strftime('%H:%M')}~{self.endtime.strftime('%H:%M')}/"


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
    priority = models.IntegerField(default=3, validators=[MinValueValidator(0), MaxValueValidator(6)])
    def __str__(self):
        return self.songname


# 곡의 세션이 누구인지 곡id(fk),이름(fk),세션 정보(v,d,g,k,b 등으로 표기하자)
class Session(models.Model):
    id = models.AutoField(primary_key=True)
    song_id = models.ForeignKey(SongData, on_delete=models.CASCADE, related_name='session')
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, related_name='session')
    instrument = models.CharField(max_length=255)
    def __str__(self) -> str:
        return ",".join([self.song_id.songname, self.user_name.username, self.instrument])
    

# 불참 사유!
class WhyNotComing(models.Model):
    id = models.AutoField(primary_key=True)
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE)
    schedule_id = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='whynotcoming')
    reason = models.CharField(max_length=255)

"""
# 지각 및 노쇼 체크용 도착시간 DB
class ArrivalTime(models.Model):
    id = models.AutoField(primary_key=True)
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, related_name='arrivaltime')
    date = models.DateField(auto_now_add=True)
    arrival_time = models.TimeField(auto_now_add=True)
    confirmed_arrival_time = models.TimeField(null=True, default=None)
    is_confirmed = models.BooleanField(default=False)
"""


# 합주 시간표
class Timetable(models.Model):
    id = models.AutoField(primary_key=True)
    schedule_id = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='timetable')
    song_id = models.ForeignKey(SongData, on_delete=models.CASCADE, related_name='timetable')
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.IntegerField(default=0)


class AttendanceCheck(models.Model):
    id = models.AutoField(primary_key=True)
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, related_name='attendancecheck')
    timetable_id = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='attendancecheck')
    arrival_time = models.TimeField(auto_now_add=True)


class KakaoTalkId(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    user_name = models.ForeignKey(PracticeUser, on_delete=models.CASCADE, related_name='kakaotalkid')