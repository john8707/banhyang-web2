from banhyang.practice.models import Schedule, Timetable, Session, Apply
from datetime import datetime

#Datetime의 요일 표시를 한글로 바꿔주는 함수
def weekday_dict(idx:int) -> str:
    """
    Datetime object의 요일 표시를 int -> 한글 string으로 변환해주는 함수
    """
    weekday_to_korean = {
        0: ' (월)',
        1: ' (화)',
        2: ' (수)',
        3: ' (목)',
        4: ' (금)',
        5: ' (토)',
        6: ' (일)'
    }
    return weekday_to_korean[idx]


def calculate_eta(user_object, date):
    """
    저장된 Timetable을 통해 유저의 예상 도착시간 계산
    """
    # 1. 불참 시간 리스트 만들기
    schedule_objects = Schedule.objects.filter(date=date)
    apply_objects_list = []
    for schedule_object in schedule_objects:
        apply_objects_list.extend(Apply.objects.filter(user_name=user_object,schedule_id=schedule_object))

    # 2. 내 연주곡 가져오기
    temp_song_play_objects = [x.song_id for x in Session.objects.filter(user_name=user_object)]
    song_play_objects = list(set(temp_song_play_objects))
    
    # 3. 확정된 스케쥴 중에서 내 연주곡 필터, 시간별로 sort
    timetable_objects = Timetable.objects.filter(song_id__in = song_play_objects, schedule_id__in=schedule_objects).order_by('start_time')

    # 4. 시간 비교, 가능시간 존재시 즉시 return
    for timetable_object in timetable_objects:
        # timetable object의 시간 format을 apply의 not available의 div에 대응되는 단위로 변경
        time_delta = int((datetime.combine(datetime.today(), timetable_object.start_time) - datetime.combine(datetime.today(),timetable_object.schedule_id.starttime)).total_seconds()/600)
        song_div_list = [x + time_delta for x in range(int(timetable_object.schedule_id.min_per_song/10))]
        apply_object = Apply.objects.filter(user_name=user_object, schedule_id=timetable_object.schedule_id, not_available__in=song_div_list)
        if not apply_object:
            return timetable_object.start_time
    
    return None


# Convert datetime object to integer(yyyymmdd)
def date_to_integer(dt_time):
    """
    Datetime object를 yyyymmdd 형식의 integer로 변환
    """
    return 10000*dt_time.year + 100*dt_time.month + dt_time.day


# Convert integer(yyyymmdd) to datetime object
def integer_to_date(dt_int):
    """
    yyyymmdd 형식의 integer을 Datetime object로 변환
    """
    int_to_string = str(dt_int)
    return datetime(int(int_to_string[0:4]), int(int_to_string[4:6]), int(int_to_string[6:8]),9,0)
