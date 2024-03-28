from django.urls import path
from . import views, chatbot

urlpatterns = [
    path('practice', views.practice_apply, name='practice_apply'),
    path('practice/setting', views.setting, name='setting'),
    path('practice/create', views.schedule_create, name='schedule_create'),
    path('practice/songs', views.song_list, name='song_list'),
    path('practice/users', views.user_list, name='user_list'),
    path('practice/timetable', views.timetable, name='timetable'),
    path('practice/delete/<int:schedule_id>', views.schedule_delete, name='schedule_delete'),
    path('practice/NA', views.who_is_not_coming, name='who_is_not_coming'),
    path('practice/attchk', views.attendance_check_per_day, name='attendance_check'),

    #chatbot api server response
    path('chatbot/attendance', chatbot.attendance_check_only_first, name='chatbot_attendance'),
    path('chatbot/register', chatbot.register, name='chatbot_register')
]