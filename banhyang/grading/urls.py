from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.google_login, name='google_login'),
    path('auth/logout/', views.google_logout, name="google_logout"),
    path('auth/callback/', views.google_callback, name='google_callback'),
    path('', views.grading_home, name='grading_home'),
    path('stream/', views.stream_grading, name='stream_grading'),
]