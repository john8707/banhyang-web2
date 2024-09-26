from ortools.linear_solver import pywraplp
import pandas as pd
from datetime import datetime, date, timedelta
from math import ceil
from collections import defaultdict

from django.db.models import Prefetch, QuerySet

from .models import SongData, PracticeUser, Schedule, Apply, Session
from banhyang.core.utils import weekday_dict


def calc_minute_delta(object:'QuerySet[Schedule]') -> int:
    """
    Schedule object를 input 받아 전체 합주 시간을 분 단위로 return
    """

    delta = (datetime.combine(date.today(), object.endtime) - datetime.combine(date.today(), object.starttime))
    return int(delta.seconds / 60)

class BaseRetriever:
    """
    Schedule, Route Optimizer에서 공통으로 사용하는 raw data의 retriever
    """
    def __init__(self) -> None:
        pass

    def retreive_common_data(self) -> dict:
        """
        유저, 곡, 세션 정보를 dict로 return
        """
        common_data = {}

        user_objects = PracticeUser.objects.prefetch_related('session')
        session_objects = Session.objects.all()
        session_qs = Session.objects.select_related('user_name')
        song_objects = SongData.objects.prefetch_related(Prefetch('session', queryset=session_qs))

        common_data['user_objects'] = user_objects
        common_data['song_objects'] = song_objects
        common_data['session_objects'] = session_objects

        return common_data


class ScheduleRetriever:
    """
    최적화 시간표를 만들기 위한 raw data를 DB 서버에서 retrieve
    """
    def __init__(self) -> None:
        # 시간표를 만들 때 현재 활성화 되어있는 합주 일정만 사용
        self.USE_CURRENT_SCHEDULE = True

    def get_parameters(self) -> dict:
        """
        가중치와 파라미터 설정
        """

        param_dict = {}

        # 세션별 가중치의 값
        session_weight_parameters = {
            'v': 1,
            'd': 2,
            'g': 1.5,
            'b': 1,
            'k': 0.8,
            'etc': 0.6
        }
        param_dict['session_weight'] = session_weight_parameters

        # Song Model의 우선 순위 별 가중치의 값
        priority_weight_parameters = {
            0: 100,
            1: 1.6,
            2: 1.3,
            3: 1,
            4: 0.7,
            5: 0.4,
            6: 0
        }
        param_dict['priority_weight'] = priority_weight_parameters

        return param_dict

    def retrieve_from_DB(self, common_data: dict) -> dict:
        """
        Raw data를 retrieve 후 dictionary로 return
        """
        raw_data = {}

        raw_data['schedule_objects'] = Schedule.objects.filter(is_current=self.USE_CURRENT_SCHEDULE).order_by('date')

        # 불참 데이터에서 not available이 -1(전체 참여)인 데이터를 제외하고 가져옴
        raw_data['unavailable_objects'] = Apply.objects.filter(schedule_id__in=raw_data['schedule_objects']).exclude(not_available=-1).select_related('user_name').select_related('schedule_id')

        raw_data['param_dict'] = self.get_parameters()

        # Base retriever에서 받아온 데이터와 합치기
        raw_data.update(common_data)

        return raw_data


class ScheduleProcessor:
    """
    Raw data를 용도에 맞게 가공하는 processor
    """
    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    def get_practice_info(self) -> dict:
        """
        합주 정보를 dictionary로 return

        {schedule id : {총 합주 시간: , 곡 당 시간: , 하루에 몇 타임: , 방 개수: , 시작 시간: , 끝 시간:}}
        """
        practice_info = {x.id: {'total_minutes': calc_minute_delta(x),  # 총 합주 시간
                                'minute_per_song': int(x.min_per_song / 10),  # 곡 당 분(10분 단위)
                                'song_per_day': ceil(calc_minute_delta(x) / int(x.min_per_song / 10) / 10),  # 하루에 몇 곡을 하는지
                                'room_count': x.rooms,  # 합주에 사용할 방의 개수
                                'start_time': x.starttime,
                                'end_time': x.endtime} for x in self.raw_data['schedule_objects']}

        return practice_info

    def get_available_dict(self, practice_info: dict) -> dict:
        """
        각 인원당 시간대별 참석 여부 Boolean List를 dictionary로 return

        {이름 : {합주 Id :[합주 시간대별 참석 여부 Bool]}}

        ex) { '김반향': {12: [0, 1, 0], 10: [1, 1, 1, 1]} }
        """
        available_dict = {}
        unavailable_dict = {}

        # 불참 여부의 boolean list를 먼저 생성
        # unavailable dict = {유저 : {합주 id : [불참 시간대]}}
        for user in [x.username for x in self.raw_data['user_objects']]:
            unavailable_dict[user] = {}
            available_dict[user] = {}
            for scheduleId in [x.id for x in self.raw_data['schedule_objects']]:
                unavailable_dict[user][scheduleId] = []

        for unavailable_object in self.raw_data['unavailable_objects']:
            unavailable_dict[unavailable_object.user_name.username][unavailable_object.schedule_id.id].append(unavailable_object.not_available)

        # unavalable dict를 이용해, 인원 별 각 시간대의 참석 가능 여부의 Boolean list 생성
        for user in [x.username for x in self.raw_data['user_objects']]:
            for scheduleId in [x.id for x in self.raw_data['schedule_objects']]:
                len_per_day = practice_info[scheduleId]['total_minutes']
                min_per_song = practice_info[scheduleId]['minute_per_song']
                available_bool_list = []
                div_sum = 0
                song_count = 0
                for i in range(ceil(len_per_day / 10)):
                    song_count += 1
                    if i not in unavailable_dict[user][scheduleId]:
                        div_sum += 1
                    if song_count == min_per_song or i + 1 == ceil(len_per_day / 10):
                        # available_bool_list.append(round(div_sum/song_count,2))
                        # 30분 합주의 일부만 못오는 것 반영하기
                        available_bool_list.append(1 if div_sum == song_count else 0)  # 일부만 못오면 불참으로 간주하기 <중요> 위와 아래 중 하나만 적용할 것!
                        div_sum = 0
                        song_count = 0

                available_dict[user][scheduleId] = available_bool_list
        return available_dict

    def get_song_session_dict(self) -> dict:
        """
        각 곡 별 악기와 인원의 dictionary를 dictionary로 return

        {곡 id : {악기 : [연주 인원]} }
        """
        song_session_dict = {}
        for song_object in self.raw_data['song_objects']:
            session_inst_dict = defaultdict(list)
            who_play_this_song = song_object.session.all()
            for session in who_play_this_song:
                session_inst_dict[session.instrument].append(session.user_name.username)
            song_session_dict[song_object.id] = dict(session_inst_dict)

        return song_session_dict

    def get_song_available_dict(self, song_session_dict: dict, practice_info: dict, available_dict: dict) -> dict:
        """
        각 곡의 세션 별, 중요도 별 가중치(가중치는 Schedule Retriever의 get_parameters에서 설정)를 반영한 시간 당 참석률을 dictionary로 return

        {곡 id : {합주 id : [시간대별 참석률]}}
        """
        song_available_dict = {}

        # 가중치 가져오기
        song_priority_dict = {x.id: x.priority for x in self.raw_data['song_objects']}
        session_weight_parameters = self.raw_data['param_dict']['session_weight']
        priority_weight_parameters = self.raw_data['param_dict']['priority_weight']

        for songId, session in song_session_dict.items():
            schedule_attendance_dict = {}

            # 해당 곡 가중치
            song_priority = priority_weight_parameters[song_priority_dict[songId]]

            for scheduleId in [x.id for x in self.raw_data['schedule_objects']]:
                attendance_rate_list = []
                song_per_day = practice_info[scheduleId]['song_per_day']
                for i in range(song_per_day):
                    attendance_sum = 0
                    total_sum = 0
                    for session_abbrev, session_name_list in session.items():
                        attendance_sum += sum([available_dict[name][scheduleId][i] for name in session_name_list]) * session_weight_parameters[session_abbrev]
                        total_sum += session_weight_parameters[session_abbrev] * len(session_name_list)
                    
                    # 최종 참석률 계산
                    attendance_rate = round(attendance_sum / total_sum, 2) * song_priority
                    attendance_rate_list.append(attendance_rate)

                schedule_attendance_dict[scheduleId] = attendance_rate_list

            song_available_dict[songId] = schedule_attendance_dict
        return song_available_dict

    def get_song_conflict_list(self, song_session_dict: dict):
        """
        song_session_set : 중복을 제거한 {곡 id : (연주 인원)} dict

        song_conflict_list : list(곡 참여자가 겹치는 두 곡)의 list
        
        """

        # {곡 id : set(연주 인원)}
        song_session_set = {}
        for songId, session_dict in song_session_dict.items():
            song_session_set[songId] = []
            for names_list in session_dict.values():
                song_session_set[songId].extend([x for x in names_list if x not in song_session_set[songId]])
            song_session_set[songId] = set(song_session_set[songId])

        # 세션 겹치는 곡 목록 생성
        song_conflict_list = []
        songId_list = [x.id for x in self.raw_data['song_objects']]

        for i in range(len(songId_list)):
            for j in range(i):
                if song_session_set[songId_list[i]].intersection(song_session_set[songId_list[j]]):
                    song_conflict_list.append([songId_list[i], songId_list[j]])

        return song_session_set, song_conflict_list

    def process(self) -> dict:
        """
        Raw data를 정제해 optimizer에 전달하는 값들을 dict로 return
        """
        processed_data = {}
        practice_info = self.get_practice_info()
        available_dict = self.get_available_dict(practice_info)
        song_session_dict = self.get_song_session_dict()
        song_available_dict = self.get_song_available_dict(song_session_dict, practice_info, available_dict)
        song_session_set, song_conflict_list = self.get_song_conflict_list(song_session_dict)

        processed_data['practice_info_dict'] = practice_info
        processed_data['scheduleId_list'] = [x.id for x in self.raw_data['schedule_objects']]
        processed_data['songId_list'] = [x.id for x in self.raw_data['song_objects']]

        processed_data['available_dict'] = available_dict
        processed_data['song_available_dict'] = song_available_dict
        processed_data['song_conflict_list'] = song_conflict_list

        # Data for Post Processing
        processed_data['song_session_set'] = song_session_set

        # {합주 id : 합주 날짜} -> 09월 21일(목) 형식
        processed_data['practiceId_to_date'] = {x.id: x.date.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape') + weekday_dict(x.date.weekday()) for x in self.raw_data['schedule_objects']}
        processed_data['songId_to_name'] = {x.id: x.songname for x in self.raw_data['song_objects']}

        return processed_data


class ScheduleOptimizer:
    """
    최적화된 시간표를 구하는 Optimizer
    """
    def __init__(self, processed_data) -> None:
        self.processed_data = processed_data
        self.solver = pywraplp.Solver('SolveAssignmentProblemMIP', pywraplp.Solver.SAT_INTEGER_PROGRAMMING)

    def time_iter(self, p) -> range:
        "제약 조건 설정할 때 합주 별 반복되는 iteration 함수화"
        return range(self.processed_data['practice_info_dict'][p]['song_per_day'])

    def add_decision_variable(self) -> None:
        """
        결정 변수 선언
        """
        self.x = {}

        for p in self.processed_data['scheduleId_list']:
            for t in self.time_iter(p):
                for s in self.processed_data['songId_list']:
                    self.x[p, t, s] = self.solver.BoolVar('self.x[%i, %i, %i]' % (p, t, s))

    def add_objective_function(self) -> None:
        """
        목적 함수 설정
        """
        self.solver.Maximize(self.solver.Sum([self.processed_data['song_available_dict'][s][p][t] * self.x[p, t, s] for s in self.processed_data['songId_list'] for p in self.processed_data['scheduleId_list'] for t in self.time_iter(p)]))

    def add_constraint(self) -> None:
        """
        제약 조건 추가
        """
        # 전체 합주 통틀어서 곡 당 최대 한번 (if 가능한 총 합주 타임이 곡의 갯수보다 많을 경우)
        for s in self.processed_data['songId_list']:
            self.solver.Add(self.solver.Sum([self.x[p, t, s] for p in self.processed_data['scheduleId_list'] for t in self.time_iter(p)]) <= 1)

        # 같은 곡은 하루에 한번만!
        for p in self.processed_data['scheduleId_list']:
            for s in self.processed_data['songId_list']:
                self.solver.Add(self.solver.Sum([self.x[p, t, s] for t in self.time_iter(p)]) <= 1)

        # required! 한 타임에 최대 곡 수는 방 갯수 만큼
        for p in self.processed_data['scheduleId_list']:
            for t in self.time_iter(p):
                self.solver.Add(self.solver.Sum([self.x[p, t, s] for s in self.processed_data['songId_list']]) <= self.processed_data['practice_info_dict'][p]['room_count'])

        # required! 같은 타임에 세션이 겹치는 곡이 없도록
        for duplicated_list in self.processed_data['song_conflict_list']:
            for p in self.processed_data['scheduleId_list']:
                for t in self.time_iter(p):
                    self.solver.Add(self.x[p, t, duplicated_list[0]] + self.x[p, t, duplicated_list[1]] <= 1)

    def optimize(self) -> dict:
        """
        Integer programming을 이용해 최적화 된 합주를 생성, 의사 결정 변수의 값들을 dict로 return
        """
        self.add_decision_variable()
        self.add_objective_function()
        self.add_constraint()

        # 최적화! -> 특정값 조회 방법 : self.x[1,3,4].solution_value()
        self.solver.Solve()
        return self.x


class SchedulePostProcessor:
    """
    optimized 된 값들을 web view를 위해 후처리하는 post processor
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
        timetable_df_dict = {}
        # 곡 별 불참 인원을 리스트로 보여주기
        not_coming_dict = {}

        # 결과값을 data frame으로! / 합주 불참자까지 나오도록
        day_count = 0
        for p in self.processed_data['scheduleId_list']:

            idx = []
            song_per_day = self.processed_data['practice_info_dict'][p]['song_per_day']
            time_count = datetime.combine(date(1, 1, 1), self.processed_data['practice_info_dict'][p]['start_time'])

            # Dataframe의 시간 index 생성
            for _ in range(song_per_day):
                idx.append(time_count.strftime('%H:%M'))
                time_count += timedelta(minutes=self.processed_data['practice_info_dict'][p]['minute_per_song'] * 10)

            # Dataframe 틀 생성
            timetable_df = pd.DataFrame(data=[], index=idx, columns=['room ' + str(room) for room in range(1, self.processed_data['practice_info_dict'][p]['room_count'] + 1)])

            # 의사 결정 변수의 값 > 0 -> 해당 타임에 해당 곡 합주가 존재한다는 뜻
            # 시간표 Dataframe에 string으로 저장
            # 불참 인원을 not_coming_dict에 넣기
            for t in self.time_iter(p):
                room_count = 0
                for s in self.processed_data['songId_list']:
                    if self.x[p, t, s].solution_value() > 0:
                        timetable_df.iloc[t, room_count] = self.processed_data['songId_to_name'][s]
                        room_count += 1
                        # 전체 불참만 보이기 ==0, 일부 불참도 보이기 <1
                        not_coming_dict[self.processed_data['songId_to_name'][s] + " (" + self.processed_data['practiceId_to_date'][p] + " " + idx[t] + ")"] = [x for x in self.processed_data['song_session_set'][s] if self.processed_data['available_dict'][x][p][t] < 1]


            timetable_df.header = "day" + str(day_count)
            day_count += 1
            timetable_df_dict[p] = timetable_df

        return timetable_df_dict, not_coming_dict


class RouteRetriever:
    """
    Route optimize에 필요한 raw data를 DB 서버에서 retrieve
    """
    def __init__(self) -> None:
        pass
    
    def get_parameters(self) -> dict:
        param_dict = {}

        session_id_dict = {
            0: 'g',
            1: 'v',
            2: 'b',
            3: 'd',
            4: 'k',
            5: 'etc'
        }
        session_weight_dict = {
            0: 1, # guitar
            1: 0, # vocal
            2: 0, # bass
            3: 0, # drum
            4: 0, # keyboard
            5: 0, # etc
        }

        param_dict['session_abb_id_dict'] = session_id_dict
        param_dict['session_weight_dict'] = session_weight_dict

        return param_dict

    def retrieve_db_data(self, common_data: dict) -> dict:
        raw_data = {}

        raw_data['param_dict'] = self.get_parameters()

        raw_data.update(common_data)

        return raw_data


class RouteProcessor:
    """
    Raw data를 용도에 맞게 가공하는 processor
    """
    def __init__(self, raw_data, schedule_dataframe) -> None:
        self.raw_data = raw_data
        self.schedule_dataframe = schedule_dataframe

    def convert_dataframe_to_list(self) -> list:
        """
        Schedule Dataframe의 곡 제목의 2d array를 곡 id의 1d array list로 변경하여 Return

        각 List는 각 타임별 곡들의 id list
        [[첫번째 타임의 곡 id 목록], [두번째 타임의 곡 id 목록] , ... ]
        """
        song_id_dict = {x.songname : x.id for x in self.raw_data['song_objects']}
        dataframe_row_list = []

        for row in self.schedule_dataframe.itertuples():
            dataframe_row_list.append(row[1:])

        schedule_id_list = []

        for row in dataframe_row_list:
            id_list = []
            total_room_number = len(row)
            for name in row:
                id_list.append(song_id_dict[name]) if name != 'X' else None
            schedule_id_list.append(id_list)

        return schedule_id_list, total_room_number

    
    def get_users_song_order(self, schedule_id_list) -> dict:
        """
        해당 schedule의 유저별 세션별 곡 순서 list를 dictionary로

        { 유저이름 : {보컬: [곡 순서 목록], 드럼: [곡 순서 목록]} } 형식의 dictionary Return
        """
        
        user_order_dict = {}
        user_objects = self.raw_data['user_objects']
        id_object = {x.id : x for x in self.raw_data['song_objects']}

        for user in user_objects:
            user_order_dict[user.username] = {'g':[], 'v':[], 'b':[], 'd':[], 'k':[], 'etc':[]}

        for id_list in schedule_id_list:
            for i in id_list:
                song_sessions = id_object[i].session.all()

                for session_object in song_sessions:
                    user_order_dict[session_object.user_name.username][session_object.instrument].append(session_object.song_id.id)

        return user_order_dict
    
    def get_id_user_dict(self) -> dict:
        """
        { id : 유저이름 } 형식의 dictionary Return

        실제 유저 id는 DB에 존재하지 않지만, optimizer 과정에서 유저의 integer index가 필요하여 임의의 id 부여
        """

        id_user_dict = {}

        n = 0
        for i in self.raw_data['user_objects']:
            id_user_dict[n] = i.username
            n += 1

        return id_user_dict
    
    def get_song_time_dict(self, schedule_id_list) -> dict:
        """
        { 곡 id : [해당 곡 time index]}
        """
        song_t_dict = {x.id : [] for x in self.raw_data['song_objects']}

        for t in range(len(schedule_id_list)):
            for i in schedule_id_list[t]:
                song_t_dict[i].append(t)

        return song_t_dict

    def process(self) -> dict:
        """
        필요한 데이터를 모두 전처리하여 dictionary에 담아 return
        """

        processed_data = {}
        schedule_id_list, total_room_number = self.convert_dataframe_to_list()

        user_order_dict = self.get_users_song_order(schedule_id_list)

        id_user_dict = self.get_id_user_dict()
        song_t_dict = self.get_song_time_dict(schedule_id_list)

        processed_data['schedule_id_list'] = schedule_id_list
        processed_data['total_room_number'] = total_room_number
        processed_data['user_order_dict'] = user_order_dict
        processed_data['id_user_dict'] = id_user_dict
        processed_data['song_t_dict'] = song_t_dict

        return processed_data


class RouteOptimizer():
    """
    방 이동 횟수를 최적화

    For further details of decision variables, objective function, or constraints, please check the each annotation.
    """
    def __init__(self, processed_data, raw_data) -> None:
        self.schedule_id_list = processed_data['schedule_id_list']
        self.total_room_number = processed_data['total_room_number']
        self.user_order_dict = processed_data['user_order_dict']
        self.id_user_dict = processed_data['id_user_dict']
        self.song_t_dict = processed_data['song_t_dict']

        self.session_id_dict = raw_data['param_dict']['session_abb_id_dict']
        self.session_weight_dict = raw_data['param_dict']['session_weight_dict']
        self.song_objects = raw_data['song_objects']

        self.solver = pywraplp.Solver('SolveAssignmentProblemMIP', pywraplp.Solver.SAT_INTEGER_PROGRAMMING)

    def add_decision_variable(self):
        """
        결정 변수 선언
        """
        self.s = {}
        self.x = {}
        self.y = {}
        # s[i,t,r] -> i: 곡 id, t: 순서, r: 방 번호인 곡
        # i의 t번째 time의 방 번호가 r인지 여부 Boolean Var
        # ex) s[1,2,3] = 1 -> 곡 1, 2번째 순서, 방 번호 3에서 합주함
        for t in range(len(self.schedule_id_list)):
            for r in range(self.total_room_number):
                for i in self.schedule_id_list[t]:
                    self.s[i, t, r] = self.solver.BoolVar('self.s[%i, %i, %i]' % (i, t, r))

        # y[p, s, n] -> p: 유저 id, s: 세션, n: n번째 곡 
        # p의 s세션 n번째 곡 이후 이동 여부 Boolean Var
        # ex) y[1,2,3] = 1 -> 유저 1의 악기 2의 3번째 곡 합주 이후, 3번째 곡의 합주 방 번호와 4번째 곡의 합주 방 번호가 다름(방 이동 해야함)
        for p in self.id_user_dict:
            for s in self.session_id_dict:
                for n in range(len(self.user_order_dict[self.id_user_dict[p]][self.session_id_dict[s]]) - 1):
                    self.y[p, s, n] = self.solver.BoolVar('self.y[%i, %i, %i]' % (p, s, n))

        # y의 값을 구하기 위한 Dummy Var x
        for p in self.id_user_dict:
            for s in self.session_id_dict:
                for n in range(len(self.user_order_dict[self.id_user_dict[p]][self.session_id_dict[s]]) - 1):
                    for r in range(self.total_room_number):
                        self.x[p, s, n, r] = self.solver.BoolVar('self.x[%i, %i, %i, %i]' % (p, s, n, r))

    def add_objective_function(self):
        """
        목적 함수 설정
        """
        # Minimize y * 세션별 weight
        # y -> 합주 후 방 이동 여부이므로 해당 값을 최소화하는 s(곡 별 방 배정)를 계산함!
        self.solver.Minimize(
            self.solver.Sum([self.y[p, s, n] * self.session_weight_dict[s]
                             for p in self.id_user_dict
                             for s in self.session_id_dict
                             for n in range(len(self.user_order_dict[self.id_user_dict[p]][self.session_id_dict[s]]) - 1)]))

    def add_constraint(self):
        """
        제약 조건 추가
        """
        # 곡 i는 t타임에서 전체 room 중 반드시 하나에만 들어가야함
        for t in range(len(self.schedule_id_list)):
            for i in self.schedule_id_list[t]:
                self.solver.Add(self.solver.Sum(self.s[i, t, r] for r in range(self.total_room_number)) == 1)

        # x = 1 -> y = 0 / x = 0 -> y = 1
        # x가 모두 0일 경우, 즉 아래 제약 조건에 의해 n번째 곡의 방과 n+1번째 곡의 방이 서로 다를 경우 이동이 발생하므로 y = 1이 되게 함
        for p in self.id_user_dict:
            for s in self.session_id_dict:
                for n in range(len(self.user_order_dict[self.id_user_dict[p]][self.session_id_dict[s]]) - 1):
                    self.solver.Add(self.y[p, s, n] + self.solver.Sum(self.x[p, s, n, r] for r in range(self.total_room_number)) == 1)        

        # 현재 곡과 다음 곡의 방이 같을 경우 x = 1이 되게 함
        for p in self.id_user_dict:
            for s in self.session_id_dict:
                t_pointer = 0
                t_pointer2 = 0
                for n in range(len(self.user_order_dict[self.id_user_dict[p]][self.session_id_dict[s]]) - 1):
                    song_id = self.user_order_dict[self.id_user_dict[p]][self.session_id_dict[s]][n]
                    song_id2 = self.user_order_dict[self.id_user_dict[p]][self.session_id_dict[s]][n + 1]
                    for t in self.song_t_dict[song_id]:
                        if t >= t_pointer:
                            t_pointer = t
                            break
                    for t in self.song_t_dict[song_id2]:
                        if t >= t_pointer2:
                            t_pointer2 = t
                            break
                    for r in range(self.total_room_number):
                            
                        self.solver.Add(self.x[p, s, n, r] <= self.s[song_id, t_pointer, r])
                        self.solver.Add(self.x[p, s, n, r] <= self.s[song_id2, t_pointer2, r])
                        self.solver.Add(self.x[p, s, n, r] >= self.s[song_id, t_pointer, r] + self.s[song_id2, t_pointer2, r] - 1)

        # 같은 t의 서로 다른 곡들은 같은 방을 사용하지 않음
        for t in range(len(self.schedule_id_list)):
            for r in range(self.total_room_number):
                self.solver.Add(self.solver.Sum(self.s[i, t, r] for i in self.schedule_id_list[t]) <= 1)

    def optimize(self):

        # s[i,t,r] -> i: 곡 id, t: 순서, r: 방 번호인 곡
        self.add_decision_variable()
        self.add_objective_function()
        self.add_constraint()

        self.solver.Solve()

        return self.s


class RoutePostProcessor:
    """
    optimized 된 값들을 web view를 위해 후처리하는 post processor
    """
    def __init__(self, optimizer:RouteOptimizer, original_dataframe) -> None:
        self.result = optimizer.s
        self.schedule_id_list = optimizer.schedule_id_list
        self.total_room_number = optimizer.total_room_number
        self.song_objects = optimizer.song_objects

        self.original_dataframe = original_dataframe

    def post_process(self):
        """
        최적화된 시간표를 바탕으로 새로운 timetable의 dataframe을 생성
        """
        id_song_dict = {x.id : x.songname for x in self.song_objects}
        new_dataframe = pd.DataFrame(data=[], index=self.original_dataframe.index, columns=self.original_dataframe.columns)
        for t in range(len(self.schedule_id_list)):
            for r in range(self.total_room_number):
                for i in self.schedule_id_list[t]:
                    if self.result[i, t, r].solution_value() > 0:
                        new_dataframe.iloc[t, r] = id_song_dict[i]

        return new_dataframe.fillna('X')


def timetable_df_to_objects(timetable_df_dict:dict, schedule_info_dict:dict, song_objects:dict) -> dict:
    """
    시간표 dataframe을 인풋으로 받아, 해당 시간표에 맞는 timetable objects로 저장하기 위한 데이터의 딕셔너리로 변환
     
    {합주 id : {곡 id : (시작 시간, 끝 시간, 방 이름)}} 형식
    """
    timetable_object_dict = {}
    song_name_to_id = {x.songname : x.id for x in song_objects}
    for i, df in timetable_df_dict.items():
        timetable_object_dict[i] = {}
        for time_count, row in enumerate(df.itertuples(index=False)):
            start_time = datetime.combine(date(1, 1, 1), schedule_info_dict[i]['start_time']) + timedelta(minutes=schedule_info_dict[i]['minute_per_song'] * 10 * time_count)
            end_time = min(start_time + timedelta(minutes=schedule_info_dict[i]['minute_per_song'] * 10), datetime.combine(date(1, 1, 1), schedule_info_dict[i]['end_time']))
            for room_count in range(len(row)):
                if row[room_count] != 'X':
                    timetable_object_dict[i][song_name_to_id[row[room_count]]] = (start_time.time(), end_time.time(), df.columns[room_count])
    return timetable_object_dict
