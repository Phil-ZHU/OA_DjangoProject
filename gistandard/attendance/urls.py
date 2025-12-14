# attendance/urls.py
from django.urls import path
from . import views

app_name = 'attendance'  # 关键：定义命名空间

urlpatterns = [
    path('', views.punch_page, name='index'),  # 访问 /attendance/ 显示打卡页面
    path('punch/', views.punch_page, name='punch_page'),  # 打卡页面
    path('punch/in/', views.punch_in, name='punch_in'),   # 上班打卡
    path('punch/out/', views.punch_out, name='punch_out'), # 下班打卡
]