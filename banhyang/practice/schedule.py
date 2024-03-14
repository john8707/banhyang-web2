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



def preprocessing():
    """
    DB에서 데이터를 가져와서 Integer Programming을 돌릴 수 있도록 가공하는 함수.
    """
    # DB에서 곡,유저,합주, 세션 정보 가져오기
    songs_objects = SongData.objects.all()
    users_objects = PracticeUser.objects.all()
    practice_objects = Schedule.objects.filter(is_current=True).order_by('date')
    session_objects = Session.objects.all()

    # 합주 곡 id의 리스트화
    songId_list = [x.id for x in songs_objects]

    # 활성화된 합주들의 id값(PK) 리스트화 -> 날짜순으로 정렬되어있다.
    practiceId_list = [x.id for x in practice_objects]

    # 세션들의 이름을 리스트화
    user_list = [x.username for x in users_objects]

    # 활성화된 합주들 불참 데이터들의 쿼리셋
    unavailable_objects = Apply.objects.filter(schedule_id__in=practiceId_list).exclude(not_available=-1)


    # 합주 id : 합주 날짜 dict -> 09월 21일(목) 형식
    from .views import weekday_dict
    practiceId_to_date = {x.id: x.date.strftime('%m월 %d일'.encode('unicode-escape').decode()).encode().decode('unicode-escape')  + weekday_dict(x.date.weekday()) for x in practice_objects}

    # 곡 id : 곡 이름 dict
    songId_to_name = {x.id : x.songname for x in songs_objects}

    


    # 각 합주 별 정보
    practice_info = {x.id:{'total_minutes' : calc_minute_delta(x), # 총 합주 시간
                           'minute_per_song' : int(x.min_per_song/10), # 곡 당 분(10분 단위)
                           'song_per_day' : ceil(calc_minute_delta(x)/int(x.min_per_song/10)/10), # 하루에 몇곡까지 하는지
                           'room_count' : x.rooms, # 합주에 사용할 방의 갯수
                           'start_time' : x.starttime,
                           'end_time' : x.endtime} 
                             for x in practice_objects}


    # unavailable_dict : 합주 불참 정보를 dict로 정리함 여기서는 단순히 몇번째 타임에 못오는지만
    # 중요! DB에는 개인의 불참 정보가 10분 단위로 나뉘어져 있기에 이 것을 곡 별 시간에 맞춰 다시 정제해준다!
    # {바냥이이름 :  {합주id : [불참 division,...] ... }
    # ex) { '김반향': {6: [5], 8: [4, 5], 9: []} }

    # available_dict : 위의 데이터를 이용해서 불참 데이터를 모든 합주 타임에 대한 참여 비율로 저장
    # 전체 참여시 1 불참시 0 20분 중 10분만 참여시 0.5 / key값은 해당 합주날짜의 db auto pk 값
    # 중요! 시간 단위는 10분이 아니라, 곡 당 합주 시간 만큼임
    # ex) 곡 당 합주 시간 30분, 그 중 2번 못오면 0.33(소수점 2자리까지)
    # ex) { '김반향': {12: [0.5, 0.5, 1.0], 10: [0.0, 0.5, 1.0, 0.5]} }
    unavailable_dict = {}
    available_dict= {}

    for user in user_list:
        unavailable_dict[user] = {}
        available_dict[user] = {}
        for practiceId in practiceId_list:
            unavailable_dict[user][practiceId] = [x.not_available for x in unavailable_objects.filter(user_name=user) if x.schedule_id.id == practiceId]
            len_per_day = practice_info[practiceId]['total_minutes']
            min_per_song = practice_info[practiceId]['minute_per_song']
            temp  = []
            div_sum = 0
            song_count = 0
            for i in range(ceil(len_per_day/10)):
                song_count += 1
                if i not in unavailable_dict[user][practiceId]:
                    div_sum += 1
                if song_count == min_per_song or i+1 == ceil(len_per_day/10):
                    #temp.append(round(div_sum/song_count,2)) #30분 합주의 일부만 못오는 것 반영하기
                    temp.append(1 if div_sum==song_count else 0) #일부만 못오면 불참으로 간주하기 <중요> 위와 아래 중 하나만 적용할 것!
                    div_sum = 0
                    song_count = 0

            available_dict[user][practiceId] = temp

    # song_session_dict = {'곡id' : {'v': [홍길동,김철수], 'g':[임재원] ...}}
    song_session_dict = {}
    for songId in songId_list:
        temp = defaultdict(list)
        who_play_this_song = session_objects.filter(song_id=songId)
        for session in who_play_this_song:
            temp[session.instrument].append(session.user_name.username)
        
        song_session_dict[songId] = dict(temp)


    # available dict를 이용해 곡 별 available dict 를 만든다(세션의 weight 적용) -> 최종 스코어의 weight값이다!
    # ex) {'곡id' : {12 : [0.7, .0.4], 10: [1,1,1]} ...]}
    # 기존의 합주 누적 데이터를 weight에 사용할지는 해보고 생각하자

    song_available_dict = {}


    # 세션별 가중치의 값
    session_weight_parameters = {
        'v' : 1,
        'd' : 2,
        'g' : 1.5,
        'b' : 1,
        'k' : 0.8,
        'etc' : 0.6
    }


    # Song List Model의 우선 순위 별 가중치의 값
    priority_weight_parameters = {
        0 : 100,
        1 : 1.6,
        2 : 1.3,
        3 : 1,
        4 : 0.7,
        5 : 0.4,
        6: 0
    }

    # song_priority_dict : 각 곡 별 우선순위를 담은 dictionray
    song_priority_dict = {x.id : x.priority for x in songs_objects}

    

    for songId, session in song_session_dict.items():
        temp_dict= {}
        for practiceId in practiceId_list:
            temp_list = []
            song_per_day = practice_info[practiceId]['song_per_day']
            for i in range(song_per_day):
                n = 0
                count = 0
                for session_abbrev, session_name_list in session.items():
                    n += sum([available_dict[name][practiceId][i] for name in session_name_list]) * session_weight_parameters[session_abbrev]
                    count += session_weight_parameters[session_abbrev] * len(session_name_list)

                temp_list.append(round(n/count,2)*priority_weight_parameters[song_priority_dict[songId]])
            
            temp_dict[practiceId] = temp_list
        
        song_available_dict[songId] = temp_dict
        

    # song_session_set = {'곡id' : {'홍길동', '김철수'}, ...'}
    # 뒤에 나올 중복 곡들 확인을 위한 변수, dict의 item은 set
    song_session_set = {}
    for i,v in song_session_dict.items():
        song_session_set[i] = []
        for names in v.values():
            song_session_set[i].extend([x for x in names if x not in song_session_set[i]])
        song_session_set[i] = set(song_session_set[i])


    # 세션 겹치는 곡 목록 생성
    song_conflict_list = []

    for i in range(len(songId_list)):
        for j in range(i):
            if song_session_set[songId_list[i]].intersection(song_session_set[songId_list[j]]):
                song_conflict_list.append([songId_list[i],songId_list[j]])


    return practiceId_list, songId_list, song_available_dict, practice_info, song_conflict_list, practiceId_to_date, songId_to_name, song_session_set, available_dict



class ScheduleOptimizer:
    def __init__(self):
        self.practiceId_list, self.songId_list, self.song_available_dict, self.practice_info, self.song_conflict_list, self.practiceId_to_date, self.songId_to_name, self.song_session_set, self.available_dict= preprocessing()

        self.preferences = {}


    
    # 제약 조건 설정할 때 반복되는 iteration 함수화
    def time_iter(self, p):
        return range(self.practice_info[p]['song_per_day'])


    
    def create_schedule(self):
        self.solver = pywraplp.Solver('SolveAssignmentProblemMIP',pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)

        self.x = {}

        # 의사 결정 변수 선언
        for p in self.practiceId_list:
            for t in self.time_iter(p):
                for s in self.songId_list:
                    self.x[p,t,s] = self.solver.BoolVar('self.x[%i, %i, %i]' % ( p,t,s))

        # 목적 함수 선언
        self.solver.Maximize(self.solver.Sum([self.song_available_dict[s][p][t] * self.x[p,t,s] for s in self.songId_list for p in self.practiceId_list for t in self.time_iter(p)]))

        ## 제약 조건 설정하기 (자세한 제약 조건 내용은 주석 참조)

        # 전체 합주 통틀어서 곡 당 최대 한번 (if 가능한 총 합주 타임이 곡의 갯수보다 많을 경우)
        for s in self.songId_list:
            self.solver.Add(self.solver.Sum([self.x[p,t,s] for p in self.practiceId_list for t in self.time_iter(p)]) <= 1)

        # 같은 곡은 하루에 한번만!
        for p in self.practiceId_list:
            for s in self.songId_list:
                self.solver.Add(self.solver.Sum([self.x[p,t,s] for t in self.time_iter(p)]) <= 1)

        # required! 한 타임에 최대 곡 수는 방 갯수 만큼
        for p in self.practiceId_list:
            for t in self.time_iter(p):
                self.solver.Add(self.solver.Sum([self.x[p, t ,s] for s in self.songId_list]) <= self.practice_info[p]['room_count'])

        # required! 같은 타임에 세션이 겹치는 곡이 없도록
        for duplicated_list in self.song_conflict_list:
            for p in self.practiceId_list:
                for t in self.time_iter(p):
                    self.solver.Add(self.x[p,t,duplicated_list[0]] + self.x[p,t,duplicated_list[1]] <= 1)

        
        # 최적화! -> 특정값 조회 방법 : self.x[1,3,4].solution_value()
        self.solver.Solve()

    def post_processing(self):
        """
        for p in self.practiceId_list:
            for t in self.time_iter(p):
                for s in self.songId_list:
                    if self.x[p,t,s].solution_value() > 0:
                        print(self.x[p,t,s])
        """

        # 웹 표시용 스트링 형식의 시간표 저장
        schedule_df_dict = {}
        # 곡 별 불참 인원을 리스트로 보여주기
        not_coming_dict = {}
        # Timetable DB 저장용 DB Object 딕셔너리 -> {합주 object : {곡 object : (시작시간, 끝시간, 방 번호), }}
        timetable_object_dict = {}

        # 결과값을 data frame으로! / 합주 불참자까지 나오도록
        day_count = 0
        for p in self.practiceId_list:

            idx = []
            song_per_day = self.practice_info[p]['song_per_day']
            time_count = datetime.combine(date(1,1,1),self.practice_info[p]['start_time'])
            
            timetable_object_dict[p] = {}

            # Dataframe의 시간 index 생성
            for _ in range(song_per_day):
                idx.append(time_count.strftime('%H:%M'))
                time_count += timedelta(minutes=self.practice_info[p]['minute_per_song']*10)
            
            # Dataframe 틀 생성
            my_df = pd.DataFrame(data=[], index=idx, columns=['room ' + str(room) for room in range(1, self.practice_info[p]['room_count'] + 1)])

            # 의사 결정 변수의 값 > 0 -> 해당 타임에 해당 곡 합주가 존재한다는 뜻
            # 시간표 Dataframe에 string으로 저장
            # object로 timetable_object_dict에 넣기
            # 불참 인원을 not_coming_dict에 넣기
            for t in self.time_iter(p):
                room_count = 0
                for s in self.songId_list:
                    if self.x[p,t,s].solution_value() > 0:
                        my_df.iloc[t, room_count] = self.songId_to_name[s]
                        room_count += 1
                        not_coming_dict[self.songId_to_name[s]+" ("+self.practiceId_to_date[p]+" "+idx[t]+")"] = [x for x in self.song_session_set[s] if self.available_dict[x][p][t] < 1] #전체 불참만 보이기 ==0, 일부 불참도 보이기 <1
                        
                        start_time = datetime.combine(date(1,1,1),self.practice_info[p]['start_time']) + timedelta(minutes=self.practice_info[p]['minute_per_song']*10*t)
                        end_time = min(start_time + timedelta(minutes=self.practice_info[p]['minute_per_song']*10), datetime.combine(date(1,1,1),self.practice_info[p]['end_time']))
                        timetable_object_dict[p][s] = (start_time.time(), end_time.time(), room_count)
            my_df.header = "day" + str(day_count)
            day_count += 1
            schedule_df_dict[self.practiceId_to_date[p]] = my_df
        return schedule_df_dict, not_coming_dict, timetable_object_dict
        
        # my_df = pd.DataFrame(data=[], index=range(1,times+1), columns=range(1,days+1))
        #TODO -> 현재 시간표의 점수(참석률)  / 기타 통계 등 / 마감시간 설정하기 / 곡 별 요일 고정 / 대쉬보드 / 로그달기 / 못오는 사람이 있을 경우 해당 사람이 겹치는 곡 동시에 하기 허용
        #TODO -> 누가 언제 안오는지 깔끔하게 보여줬으면 좋겠다.
        #TODO 불참 사유도 받았으면 좋겠어용
        #TODO 에러 났을 때, 건의사항 등을 남길 수 있는 어드민 전용 페이지가 있음 좋겠다 -> 결국 게시판 기능이 필요하긴할듯 여기에 실행방법도 남기면 될듯
        #TODO 곡 세션 수정하기 기능
        #TODO 곡 당 갯수, 방 갯수 수정 기능


# old version
class Old_ScheduleOptimizer:
    def create(days, times, final, value, intervals, overlap_song_list, songlist, member_date):
        solver = pywraplp.Solver('SolveAssignmentProblemMIP',
                        pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)

        x = {}

        for i in range(days):
            for j in range(times):
                for k in range(len(final)):
                    x[i, j, k] = solver.BoolVar('x[%i, %i, %i]' % (i, j ,k))

        solver.Maximize(solver.Sum([value[i][j][k] * x[i, j, k] for i in range(days) for j in range(times) for k in range(len(final))]))
        
        #곡당 2번 이하
        for k in final:
            solver.Add(solver.Sum([x[i, j, k] for i in range(days) for j in range(times)]) <= 2)
        
        #곡당 1번 이상
        for k in final:
            solver.Add(solver.Sum([x[i, j, k] for i in range(days) for j in range(times)]) >= 1)

        """
        #곡당 정해진 수 만큼
        
        for k in final:
            solver.Add(solver.Sum([x[i, j, k] for i in range(days) for j in range(times)]) <= final[k][2][0])
        """
        #하루에 한번만
        for k in final:
            for i in range(days):
                solver.Add(solver.Sum([x[i, j, k] for j in range(times)]) <= 1)

        #한 타임에 곡 수는 방 수 만큼
        for i in range(days):
            for j in range(times):
                solver.Add(solver.Sum([x[i, j, k] for k in final]) <= intervals[i+1][2])
        
        #중복 검사
        cons_dup_check = []
        for k1 in final:
            for k2 in final:
                cons_dup_check = [final[k1][0],final[k2][0]]
                cons_dup_check.sort()
                if k1 != k2 and cons_dup_check in overlap_song_list:
                    for i in range(days):
                        for j in range(times):
                            solver.Add( x[i, j, k1] + x[i, j, k2] <= 1)

        #합주 없는 시간은 다 0으로
        for i in range(days):
            if intervals[i+1][0]*intervals[i+1][1] < times:
                solver.Add(solver.Sum([x[i, j, k] for j in range(intervals[i+1][0]*intervals[i+1][1] , times) for k in final]) == 0)
        
        sol = solver.Solve()
        finallist=[]

        for i in range(days):
            for j in range(times):
                for k in final:
                    if x[i, j, k].solution_value() > 0:
                        finallist.append([i+1, j+1, final[k][0]])



        newlist = []
        for i in finallist:
            for j in finallist:
                if i[0] == j[0] and i[1] == j[1] and i!=j:
                    temp = i[2]
                    i[2] = (temp, j[2])
                    finallist.remove(j)
                    
        my_df = pd.DataFrame(data=[], index=range(1,times+1), columns=range(1,days+1))


        for i in range(1,times+1):
            for j in range(1,days+1):
                my_df[j][i] = 0
        for i in finallist:
            a = i[0]
            b = i[1]
            name1 = i[2]
            my_df[a][b] = name1

        who_is_not_comming = []

        for i in finallist:
            for j in final:
                if type(i[2]) == tuple:
                    for k in i[2]:
                        if k == final[j][0]:
                            member = songlist[k]
                            member_av = []
                            member_un = []
                            for mem in member:
                                if mem:
                                    if member_date[mem][i[0]-1][i[1]-1] == 1:
                                        member_av.append(mem)
                                    else:
                                        member_un.append(mem)
                            who_is_not_comming.append((k, member_av, "/", member_un))
                else:
                    if i[2] == final[j][0]:
                        member = songlist[i[2]]
                        member_av = []
                        member_un = []
                        for mem in member:
                            if mem:
                                if member_date[mem][i[0]-1][i[1]-1] == 1:
                                    member_av.append(mem)
                                else:
                                    member_un.append(mem)
                        who_is_not_comming.append((i[2], member_av, "/", member_un))
        
        
        return pd.DataFrame(my_df), finallist, solver, who_is_not_comming
