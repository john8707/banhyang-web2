from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('accounting', views.accounting_main, name='accounting_main'),
    path('accounting/create', views.accounting_create, name='accounting_create'),
    path('accounting/<int:id>', views.accounting_details, name='accounting_details'),
    path('accounting/<int:accounting_id>/<int:detail_id>', views.accounting_details_delete, name='accounting_details_delete'),
    path('concert', views.concert, name='concert'),
    path('concert/create', views.concert_create, name='concert_create'),
    path('concert/apply', views.concert_apply, name='concert_apply'),
]