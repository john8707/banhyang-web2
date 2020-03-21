from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('accounting', views.accounting_main, name='accounting_main'),
    path('accounting/create', views.accounting_create, name='accounting_create'),
]