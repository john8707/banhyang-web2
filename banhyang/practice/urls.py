from django.urls import path
from . import views

urlpatterns = [
    path('practice', views.practice, name='practice'),
    path('practice/setting', views.setting, name='setting'),
    path('practice/create', views.create, name='create'),
    path('practice/songs', views.song_list, name='song_list'),
    path('practice/users', views.user_list, name='user_list'),
    path('practice/schedule/create', views.schedule_create, name='schedule_create'),
    path('practice/schedule/<int:schedule_id>', views.practice_delete, name='practice_delete'),
    path('practice/schedule/NA', views.who_is_not_coming, name='who_is_not_coming')
]