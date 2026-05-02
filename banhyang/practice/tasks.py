from celery import shared_task
import pandas as pd
from .models import SongData
from .timetable import ScheduleOptimizer, RouteOptimizer, get_all_na_users

def core_timetable_logic():
    schedule_opt = ScheduleOptimizer()
    schedule_opt.retreive_data()
    schedule_opt.process()
    schedule_opt.optimize()
    schedule_df_dict, na_indexes = schedule_opt.post_process()

    schedule_df_dict = {i: v.fillna("X") for i, v in schedule_df_dict.items()}
    
    # 동선 최적화
    for i, df in schedule_df_dict.items():
        route_opt = RouteOptimizer(df)
        route_opt.retreive_data()
        route_opt.process()
        route_opt.optimize()
        new_dataframe = route_opt.post_process()
        schedule_df_dict[i] = new_dataframe

    # [중요] Pandas DataFrame을 Celery가 주고받을 수 있는 JSON 형태로 직렬화 (쪼개기)
    df_dict_json = {}
    schedule_df_result_json = {}
    
    for i, df in schedule_df_dict.items():
        df_dict_json[i] = {
            'columns': df.columns.tolist(),
            'index': df.index.tolist(),
            'data': df.values.tolist()
        }
        date_str = schedule_opt.practiceId_to_date[i]
        schedule_df_result_json[date_str] = [i, df_dict_json[i]]
        na_indexes[i].append(date_str)

    # 쿼리셋을 리스트로 변환
    na_songs = list(SongData.objects.filter(priority=-1).values_list('songname', flat=True))

    na_users = get_all_na_users(schedule_opt.available_dict, 
                                schedule_opt.song_session_set, 
                                schedule_opt.songId_to_name)

    return {
        'df_json': schedule_df_result_json,
        'na_songs': na_songs,
        'na_users': na_users,
        'na_indexes': na_indexes
    }

@shared_task
def generate_timetable_task():
    return core_timetable_logic()