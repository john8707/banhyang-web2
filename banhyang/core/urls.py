from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('accounting', views.accounting_main, name='accounting_main'),
    path('accounting/create', views.accounting_create, name='accounting_create'),
    path('accounting/<int:id>', views.accounting_details, name='accounting_details'),
    path('accounting/<int:accounting_id>/<int:detail_id>', views.accounting_details_delete, name='accounting_details_delete'),
    path('practice', views.practice, name='practice'),
    path('practice/setting', views.practice_setting, name='practice_setting'),
    path('practice/create', views.practice_create, name='practice_create'),
    path('practice/songs', views.practice_song_list, name='practice_song_list'),
    path('practice/songs/<int:song_id>', views.practice_song_delete, name='practice_song_delete'),
]