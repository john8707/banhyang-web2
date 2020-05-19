from django.urls import path
from . import views

urlpatterns = [
    path('practice', views.practice, name='practice'),
    path('practice/setting', views.setting, name='setting'),
    path('practice/create', views.create, name='create'),
    path('practice/songs', views.song_list, name='song_list'),
    path('practice/songs/<int:song_id>', views.song_delete, name='song_delete'),
    path('practice/users', views.user_list, name='user_list'),
    path('practice/users/<username>', views.user_delete, name='user_delete'),
    path('practice/schedule/create', views.schedule_create, name='schedule_create')
]