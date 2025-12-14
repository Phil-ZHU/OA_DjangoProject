from django.urls import path
from . import views

app_name = 'oasystem'

urlpatterns = [
    path('users/', views.user_list, name='user_list'),

    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/del/', views.user_del, name='user_del'),
    path('users/<int:pk>/change_status/', views.change_status, name='change_status'),
    path('users/import/', views.user_import, name='user_import'),
    path('org/', views.org_chart, name='org_chart'),
    path('', views.dashboard, name='dashboard'),
    path('export/users/', views.export_users, name='export_users'),
    path('dashboard/', views.dashboard, name='dashboard'),
]