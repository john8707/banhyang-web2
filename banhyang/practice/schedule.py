from ortools.linear_solver import pywraplp
from .models import SongData, PracticeUser, Schedule, Apply, Session
import os
import pandas as pd
from datetime import datetime,date, timedelta
from math import ceil
from collections import defaultdict


# 합주 object input하면 합주가 총 몇시간인지 구하는 함수
def calc_minute_delta(object) -> int:

    delta = (datetime.combine(date.today(), object.endtime) - datetime.combine(date.today(), object.starttime))
    return int(delta.seconds/60)


class ScheduleRetreiver:
    """
    Retreive Raw Data from Database Server to Make Optimized Timetables.

    """
    def __init__(self) -> None:
        self.USE_CURRENT_SCHEDULE = True

    
    def get_parameters(self) -> dict:
        """"
        Get weights and preferences
        """

        param_dict = {}

        # 세션별 가중치의 값
        session_weight_parameters = {
            'v' : 1,
            'd' : 2,
            'g' : 1.5,
            'b' : 1,
            'k' : 0.8,
            'etc' : 0.6
        }
        param_dict['session_weight'] = session_weight_parameters


        # Song Model의 우선 순위 별 가중치의 값
        priority_weight_parameters = {
            0 : 100,
            1 : 1.6,
            2 : 1.3,
            3 : 1,
            4 : 0.7,
            5 : 0.4,
            6: 0
        }
        param_dict['priority_weight'] = priority_weight_parameters


        return param_dict
    

    def retreive_from_DB(self) -> dict:
        """
        DB에서 Raw 데이터 받아와 dict로 return.
        """
        raw_data = {}
        raw_data['song_objects'] = SongData.objects.all()
        raw_data['user_objects'] = PracticeUser.objects.all()
        raw_data['schedule_objects'] = Schedule.objects.filter(is_current=self.USE_CURRENT_SCHEDULE).order_by('date')
        raw_data['session_objects'] = Session.objects.all()
        raw_data['unavailable_objects'] = Apply.objects.filter(schedule_id__in=raw_data['schedule_objects']).exclude(not_available=-1)

        raw_data['param_dict'] = self.get_parameters()

        return raw_data
    

class ScheduleProcessor:
    """
    Process Raw data for Schedule Optimizer.

    """
    def __init__(self, raw_data:dict) -> None:
        self.raw_data = raw_data


    def create_practice_info(self) -> None:
        """
        Change Schedule Objects to dictionary
        """
        practice_info = {x.id:{'total_minutes' : calc_minute_delta(x), # 총 합주 시간
                            'minute_per_song' : int(x.min_per_song/10), # 곡 당 분(10분 단위)
                            'song_per_day' : ceil(calc_minute_delta(x)/int(x.min_per_song/10)/10), # 하루에 몇곡까지 하는지
                            'room_count' : x.rooms, # 합주에 사용할 방의 갯수
                            'start_time' : x.starttime,
                            'end_time' : x.endtime} 
                                for x in self.raw_data['schedule_objects']}
        
        self.practice_info = practice_info


    def create_available_dict(self) -> None:
        """
        Create available dict -> {이름 : {합주 Id :[한 곡 합주하는 시간만큼의 참석 여부 Bool]}}
        ex) { '김반향': {12: [0, 1, 0], 10: [1, 1, 1, 1]} }
        """
        available_dict = {}
        unavailable_dict = {}
        practice_info = self.practice_info
        for user in [x.username for x in self.raw_data['user_objects']]:
            unavailable_dict[user] = {}
            available_dict[user] = {}
            for scheduleId in [x.id for x in self.raw_data['schedule_objects']]:
                unavailable_dict[user][scheduleId] = [x.not_available for x in self.raw_data['unavailable_objects'].filter(user_name=user) if x.schedule_id.id == scheduleId]
                len_per_day = practice_info[scheduleId]['total_minutes']
                min_per_song = practice_info[scheduleId]['minute_per_song']
                temp  = []
                div_sum = 0
                song_count = 0
                for i in range(ceil(len_per_day/10)):
                    song_count += 1
                    if i not in unavailable_dict[user][scheduleId]:
                        div_sum += 1
                    if song_count == min_per_song or i+1 == ceil(len_per_day/10):
                        #temp.append(round(div_sum/song_count,2)) #30분 합주의 일부만 못오는 것 반영하기
                        temp.append(1 if div_sum==song_count else 0) #일부만 못오면 불참으로 간주하기 <중요> 위와 아래 중 하나만 적용할 것!
                        div_sum = 0
                        song_count = 0

                available_dict[user][scheduleId] = temp
        self.available_dict = available_dict


    def create_song_session_dict(self) -> None:
        """
        {곡 id : [곡 참여자 목록]}형태의 dict로 생성
        """
        song_session_dict = {}
        for songId in [x.id for x in self.raw_data['song_objects']]:
            temp = defaultdict(list)
            who_play_this_song = self.raw_data['session_objects'].filter(song_id=songId)
            for session in who_play_this_song:
                temp[session.instrument].append(session.user_name.username)
            song_session_dict[songId] = dict(temp)

        self.song_session_dict = song_session_dict
    

    def create_song_available_dict(self) -> None:
        song_available_dict ={}
        song_priority_dict = {x.id : x.priority for x in self.raw_data['song_objects']}
        session_weight_parameters = self.raw_data['param_dict']['session_weight']
        priority_weight_parameters = self.raw_data['param_dict']['priority_weight']


        for songId, session in self.song_session_dict.items():
            temp_dict= {}
            for scheduleId in [x.id for x in self.raw_data['schedule_objects']]:
                temp_list = []
                song_per_day = self.practice_info[scheduleId]['song_per_day']
                for i in range(song_per_day):
                    n = 0
                    count = 0
                    for session_abbrev, session_name_list in session.items():
                        n += sum([self.available_dict[name][scheduleId][i] for name in session_name_list]) * session_weight_parameters[session_abbrev]
                        count += session_weight_parameters[session_abbrev] * len(session_name_list)

                    temp_list.append(round(n/count,2)*priority_weight_parameters[song_priority_dict[songId]])
                
                temp_dict[scheduleId] = temp_list
            
            song_available_dict[songId] = temp_dict
        self.song_available_dict = song_available_dict


    def create_song_conflict_list(self) -> None:
        """
        참여 인원이 겹치는 2곡의 리스트의 리스트 생성
        """
        song_session_set = {}
        for i,v in self.song_session_dict.items():
            song_session_set[i] = []
            for names in v.values():
                song_session_set[i].extend([x for x in names if x not in song_session_set[i]])
            song_session_set[i] = set(song_session_set[i])

        self.song_session_set = song_session_set

        # 세션 겹치는 곡 목록 생성
        song_conflict_list = []
        songId_list = [x.id for x in self.raw_data['song_objects']]

        for i in range(len(songId_list)):
            for j in range(i):
                if song_session_set[songId_list[i]].intersection(song_session_set[songId_list[j]]):
                    song_conflict_list.append([songId_list[i],songId_list[j]])


        self.song_conflict_list = song_conflict_list


    def process(self) -> dict:
        """
        Raw data를 정제해 optimizer에 전달하는 값들을 dict로 return
        """
        processed_data = {}
        self.create_practice_info()
        self.create_available_dict()
        self.create_song_session_dict()
        self.create_song_available_dict()
        self.create_song_conflict_list()

        processed_data['practice_info_dict'] = self.practice_info
        processed_data['scheduleId_list'] = [x.id for x in self.raw_data['schedule_objects']]
        processed_data['songId_list'] = [x.id for x in self.raw_data['song_objects']]



        processed_data['available_dict'] = self.available_dict
        processed_data['song_available_dict'] = self.song_available_dict
        processed_data['song_conflict_list'] = self.song_conflict_list
        

        # Data for Post Processing
        processed_data['song_session_set'] = self.song_session_set
        #{합주 id : 합주 날짜} -> 09월 21일(목) 형식
        from .views import weekday_dict
        processed_data['practiceId_to_date'] = {x.id: x.date.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape')  + weekday_dict(x.date.weekday()) for x in self.raw_data['schedule_objects']}
        processed_data['songId_to_name'] = {x.id : x.songname for x in self.raw_data['song_objects']}


        return processed_data


class ScheduleOptimizer:
    """
    Create Optimized Timetables.
    """
    def __init__(self, processed_data) -> None:
        self.processed_data = processed_data


    def time_iter(self, p) -> range:
        "제약 조건 설정할 때 합주 별 반복되는 iteration 함수화"
        return range(self.processed_data['practice_info_dict'][p]['song_per_day'])
    

    def optimize(self) -> dict:
        """
        Integer programming을 이용해 최적화 된 합주를 생성, 의사 결정 변수의 값들을 dict로 return
        """
        self.solver = pywraplp.Solver('SolveAssignmentProblemMIP',pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)

        self.x = {}

        # 의사 결정 변수 선언
        for p in self.processed_data['scheduleId_list']:
            for t in self.time_iter(p):
                for s in self.processed_data['songId_list']:
                    self.x[p,t,s] = self.solver.BoolVar('self.x[%i, %i, %i]' % ( p,t,s))

        # 목적 함수 선언
        self.solver.Maximize(self.solver.Sum([self.processed_data['song_available_dict'][s][p][t] * self.x[p,t,s] for s in self.processed_data['songId_list'] for p in self.processed_data['scheduleId_list'] for t in self.time_iter(p)]))

        ## 제약 조건 설정하기 (자세한 제약 조건 내용은 주석 참조)

        # 전체 합주 통틀어서 곡 당 최대 한번 (if 가능한 총 합주 타임이 곡의 갯수보다 많을 경우)
        for s in self.processed_data['songId_list']:
            self.solver.Add(self.solver.Sum([self.x[p,t,s] for p in self.processed_data['scheduleId_list'] for t in self.time_iter(p)]) <= 1)

        # 같은 곡은 하루에 한번만!
        for p in self.processed_data['scheduleId_list']:
            for s in self.processed_data['songId_list']:
                self.solver.Add(self.solver.Sum([self.x[p,t,s] for t in self.time_iter(p)]) <= 1)

        # required! 한 타임에 최대 곡 수는 방 갯수 만큼
        for p in self.processed_data['scheduleId_list']:
            for t in self.time_iter(p):
                self.solver.Add(self.solver.Sum([self.x[p, t ,s] for s in self.processed_data['songId_list']]) <= self.processed_data['practice_info_dict'][p]['room_count'])

        # required! 같은 타임에 세션이 겹치는 곡이 없도록
        for duplicated_list in self.processed_data['song_conflict_list']:
            for p in self.processed_data['scheduleId_list']:
                for t in self.time_iter(p):
                    self.solver.Add(self.x[p,t,duplicated_list[0]] + self.x[p,t,duplicated_list[1]] <= 1)

        
        # 최적화! -> 특정값 조회 방법 : self.x[1,3,4].solution_value()
        self.solver.Solve()

        return self.x


class SchedulePostProcessor:
    """
    Post Process optimized timetable for web view
    """
    def __init__(self, result, processed_data) -> None:
        self.x = result
        self.processed_data = processed_data


    def time_iter(self, p) -> range:
        "제약 조건 설정할 때 합주 별 반복되는 iteration 함수화"
        return range(self.processed_data['practice_info_dict'][p]['song_per_day'])
    

    def post_process(self):
        """
        optimize 된 결정 변수 값들을 dataframe의 dict, object의 dict로 변경하여 return
        곡 별 불참 인원을 dict로 return
        """
         # 웹 표시용 스트링 형식의 시간표 저장
        schedule_df_dict = {}
        # 곡 별 불참 인원을 리스트로 보여주기
        not_coming_dict = {}
        # Timetable DB 저장용 DB Object 딕셔너리 -> {합주 object : {곡 object : (시작시간, 끝시간, 방 번호), }}
        timetable_object_dict = {}

        # 결과값을 data frame으로! / 합주 불참자까지 나오도록
        day_count = 0
        for p in self.processed_data['scheduleId_list']:

            idx = []
            song_per_day = self.processed_data['practice_info_dict'][p]['song_per_day']
            time_count = datetime.combine(date(1,1,1),self.processed_data['practice_info_dict'][p]['start_time'])
            
            timetable_object_dict[p] = {}

            # Dataframe의 시간 index 생성
            for _ in range(song_per_day):
                idx.append(time_count.strftime('%H:%M'))
                time_count += timedelta(minutes=self.processed_data['practice_info_dict'][p]['minute_per_song']*10)
            
            # Dataframe 틀 생성
            my_df = pd.DataFrame(data=[], index=idx, columns=['room ' + str(room) for room in range(1, self.processed_data['practice_info_dict'][p]['room_count'] + 1)])

            # 의사 결정 변수의 값 > 0 -> 해당 타임에 해당 곡 합주가 존재한다는 뜻
            # 시간표 Dataframe에 string으로 저장
            # object로 timetable_object_dict에 넣기
            # 불참 인원을 not_coming_dict에 넣기
            for t in self.time_iter(p):
                room_count = 0
                for s in self.processed_data['songId_list']:
                    if self.x[p,t,s].solution_value() > 0:
                        my_df.iloc[t, room_count] = self.processed_data['songId_to_name'][s]
                        room_count += 1
                        not_coming_dict[self.processed_data['songId_to_name'][s]+" ("+self.processed_data['practiceId_to_date'][p]+" "+idx[t]+")"] = [x for x in self.processed_data['song_session_set'][s] if self.processed_data['available_dict'][x][p][t] < 1] #전체 불참만 보이기 ==0, 일부 불참도 보이기 <1
                        
                        start_time = datetime.combine(date(1,1,1),self.processed_data['practice_info_dict'][p]['start_time']) + timedelta(minutes=self.processed_data['practice_info_dict'][p]['minute_per_song']*10*t)
                        end_time = min(start_time + timedelta(minutes=self.processed_data['practice_info_dict'][p]['minute_per_song']*10), datetime.combine(date(1,1,1),self.processed_data['practice_info_dict'][p]['end_time']))
                        timetable_object_dict[p][s] = (start_time.time(), end_time.time(), room_count)
            my_df.header = "day" + str(day_count)
            day_count += 1
            schedule_df_dict[self.processed_data['practiceId_to_date'][p]] = my_df
        return schedule_df_dict, not_coming_dict, timetable_object_dict