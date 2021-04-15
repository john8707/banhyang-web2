from ortools.linear_solver import pywraplp
import os
import pandas as pd


class Create:
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
