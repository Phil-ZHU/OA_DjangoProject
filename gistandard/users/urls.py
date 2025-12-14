from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views
from oasystem import views as oa_views  # 导入oasystem的视图，别名避免冲突
from .views import MyLoginView
app_name = 'users'
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', MyLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),
]