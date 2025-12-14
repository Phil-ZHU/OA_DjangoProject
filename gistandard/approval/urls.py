from django.urls import path
from . import views
app_name = 'approval'
urlpatterns = [
    path('leave/create/', views.leave_create, name='leave_create'),
    path('leave/', views.leave_list, name='leave_list'),
    path('leave/<str:sn>/', views.leave_detail, name='leave_detail'),
    path('pending/', views.pending_list, name='pending_list'),
    path('approve/<str:sn>/', views.approve_action, name='approve_action'),
    path('api/pending-count/', views.pending_count_api, name='pending_count_api'),


]