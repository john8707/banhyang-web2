import mimetypes
from django.urls import path, include
from django.contrib.auth import views as auth_view
from . import views, chatbot
import debug_toolbar
from banhyang.config import settings


urlpatterns = [
    path('signup', views.signup, name='signup'),
    path('login', views.login, name='login'),
    path('logout', auth_view.LogoutView.as_view(), name='logout'),
    path('user/modify', views.user_modify, name='user_modify'),
    path('user/password/modify', views.password_modify, name='password_modify'),
    path('practice', views.practice_apply, name='practice_apply'),
    path('practice/setting', views.setting, name='setting'),
    path('practice/create', views.schedule_create, name='schedule_create'),
    path('practice/songs', views.song_list, name='song_list'),
    path('practice/users', views.user_confirm_list, name='user_confirm_list'),
    path('practice/users/<int:user_id>', views.grant_admin, name='grant_admin'),
    path('practice/timetable', views.timetable, name='timetable'),
    # 비동기 status 및 result 확인용
    path('practice/timetable/status/<str:task_id>', views.check_task_status, name='check_task_status'),
    path('practice/timetable/result/<str:task_id>', views.timetable_result, name='timetable_result'),
    path('practice/delete/<int:schedule_id>', views.schedule_delete, name='schedule_delete'),
    path('practice/NA', views.who_is_not_coming, name='who_is_not_coming'),
    path('practice/attchk', views.attendance_check_index, name='attendance_check'),
    path('practice/attchk/<int:date>', views.get_attendance_check, name="get_attendance"),
    path('practice/metrics', views.metrics, name='metrics'),

    # chatbot api server response
    path('chatbot/attendance', chatbot.attendance_check_only_first, name='chatbot_attendance'),
    path('chatbot/register', chatbot.register, name='chatbot_register')
]

if settings.DEBUG:
    mimetypes.add_type("application/javascript", ".js", True)
    urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
