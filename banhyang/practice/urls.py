import mimetypes
from django.urls import path, include
from . import views, chatbot
import debug_toolbar
from banhyang.config import settings

urlpatterns = [
    path('practice', views.practice_apply, name='practice_apply'),
    path('practice/setting', views.setting, name='setting'),
    path('practice/create', views.schedule_create, name='schedule_create'),
    path('practice/songs', views.song_list, name='song_list'),
    path('practice/users', views.user_list, name='user_list'),
    path('practice/timetable', views.timetable, name='timetable'),
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
