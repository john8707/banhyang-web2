from collections import defaultdict
from datetime import datetime, date, timedelta
from math import ceil
from statistics import mean
from typing import Tuple


from django.db.models import Prefetch, QuerySet


from .models import Timetable, Session, SongData, Schedule, Apply, PracticeUser
from .schedule import calc_minute_delta


class AttendanceStatistics():
    def __init__(self) -> None:
        pass


    # {곡 id : 인원 리스트의 dictionary} 생성
    def _get_session_player(self) -> dict:
        song_session_dict = {}

        # 곡 -> 세션 -> 유저로 이어지는 DB 데이터를 쿼리 1번으로 불러오기
        session_qs = Session.objects.select_related('user_name')
        song_objects = SongData.objects.prefetch_related(Prefetch('session', queryset=session_qs))

        # {곡 id : [참여자 이름 목록]}, 한 곡에서 한 명이 여러 세션(ex 기타 & 보컬)도 가능하기에, 중복 제거 위해 list -> set -> list로 변환
        for song_object in song_objects:
            song_session_dict[song_object.id] = list(set([session.user_name.username for session in song_object.session.all()]))

        return song_session_dict


    # 합주 id를 받아 해당 합주의 각 시간대별 불참 인원 리스트를 dict로 리턴
    def _get_absentee_per_time(self, schedule_id:int) -> dict:
        schedule_object = Schedule.objects.get(id=schedule_id)
        min_per_song = int(schedule_object.min_per_song / 10)
        time_count = 0
        
        apply_objects = Apply.objects.select_related('user_name')

        absentee_dict = {}
        song_per_day = ceil(calc_minute_delta(schedule_object) / int(min_per_song) / 10)

        while time_count < song_per_day:
            start_time = datetime.combine(date(1, 1, 1), schedule_object.starttime) + timedelta(minutes=min_per_song * 10 * time_count)
            filtered_apply_objects = apply_objects.filter(schedule_id=schedule_id, not_available__in=range(time_count * min_per_song, (time_count + 1) * min_per_song))
            distinct_by_name = filtered_apply_objects.distinct().values_list('user_name')
            absentee_dict[start_time.time()] = [x[0] for x in distinct_by_name]

            time_count += 1
        return absentee_dict


    # 타임테이블 object를 받아 참석, 불참 인원 리스트의 튜플로 리턴
    def _get_attendance_per_timetable(self, timetable_obj:'QuerySet[Timetable]', absentee_dict:dict, song_session_dict:dict) -> Tuple[list, list]:
        song_id = timetable_obj.song_id
        session_list = song_session_dict[song_id.id]
        absentee_list = absentee_dict[timetable_obj.start_time]
        return list(set(session_list) - set(absentee_list)), list(set(session_list) & set(absentee_list))


    # 각 스케쥴별 참석률을 dict로 리턴
    def _get_attendance_percantage_per_schedule(self, total_att_abs_counter:dict) -> dict:
        schedule_attendance_percentage_dict = {}
        for schedule_id, song_counter_dict in total_att_abs_counter.items():
            count = [0, 0]
            for song_counter in song_counter_dict.values():
                count[0] += song_counter[0]
                count[1] += song_counter[1]
            if count[0] + count[1] > 0:
                schedule_attendance_percentage_dict[schedule_id] = round(count[0] / (count[0] + count[1]), 2) * 100
        return schedule_attendance_percentage_dict


    # 각 곡별 참석률을 dict로 리턴
    def _get_attendance_percantage_per_song(self, total_att_abs_counter:dict) -> defaultdict:
        song_attendance_percentage_dict = defaultdict(list)
        for v in total_att_abs_counter.values():
            for song_name, count in v.items():
                if count[0]+ count[1] > 0:
                    song_attendance_percentage_dict[song_name].append(round(count[0] / (count[0] + count[1]), 2))

        for i, v in song_attendance_percentage_dict.items():
            song_attendance_percentage_dict[i] = round(mean(v),2) * 100

        return song_attendance_percentage_dict


    # 각 인원 별 참석률을 dict로 리턴
    def _get_attendance_percantage_per_user(self, user_att_abs_counter:dict) -> dict:
        user_attendance_percentage_dict = {}

        for user, counter_list in user_att_abs_counter.items():
            if counter_list[0] + counter_list[1] > 0:
                user_attendance_percentage_dict[user] = round(counter_list[0] / (counter_list[0] + counter_list[1]), 2) * 100
            else:
                user_attendance_percentage_dict[user] = 0
        return user_attendance_percentage_dict

    def get_metrics(self) -> Tuple[dict, dict, defaultdict, float]:
        """
        유저 별 참석률, 합주 일자 별 참석률, 곡 별 참석률, 전체 참석률을 리턴
        """
        schedule_objects = Schedule.objects.all()
        user_objects = PracticeUser.objects.all()

        # {합주 id : {곡 id : ({참여자] , [불참자]})}}
        schedule_song_attendance_dict = {}

        # 유저별 참석, 불참 수 카운터
        user_att_abs_counter = {x.username : [0,0] for x in user_objects}

        # {합주 id : {곡 id : [참석, 불참 수]}}
        total_att_abs_counter = {}

        song_session_dict = self._get_session_player()

        for schedule_object in schedule_objects:
            schedule_id = schedule_object.id
            absentee_dict = self._get_absentee_per_time(schedule_id)
            timetable_objects = Timetable.objects.filter(schedule_id=schedule_id).select_related('song_id')

            schedule_song_attendance_dict[schedule_id] = {}

            for timetable_object in timetable_objects:
                schedule_song_attendance_dict[schedule_id][timetable_object.song_id] = self._get_attendance_per_timetable(timetable_object, absentee_dict, song_session_dict)
        

        for schedule_id, song_dict in schedule_song_attendance_dict.items():
            total_att_abs_counter[schedule_id] = {}
            for song_obj, attendance_tuple in song_dict.items():
                total_att_abs_counter[schedule_id][song_obj] = [len(attendance_tuple[0]), len(attendance_tuple[1])]
                for att in attendance_tuple[0]:
                    user_att_abs_counter[att][0] += 1
                for abs in attendance_tuple[1]:
                    user_att_abs_counter[abs][1] += 1

        percentage_user = self._get_attendance_percantage_per_user(user_att_abs_counter)
        percentage_schedule = self._get_attendance_percantage_per_schedule(total_att_abs_counter)
        percentage_song = self._get_attendance_percantage_per_song(total_att_abs_counter)
        percentage_total = round(mean(percentage_schedule.values()), 2)

        return percentage_user, percentage_schedule, percentage_song, percentage_total
