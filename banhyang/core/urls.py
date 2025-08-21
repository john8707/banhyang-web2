from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('new_index', views.new_index, name='new_index'),
    path('new_login', views.new_login, name='new_login'),
    path('new_signup', views.new_signup, name='new_signup'),
]