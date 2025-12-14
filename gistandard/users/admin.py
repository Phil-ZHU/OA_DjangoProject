from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)   # 关键：把 User 注册到后台
class UserAdmin(BaseUserAdmin):
    # 在“列表”页显示的列
    list_display = ['username', 'name', 'department', 'position', 'phone', 'date_joined']
    list_filter = ['department', 'is_staff', 'is_superuser']
    search_fields = ['username', 'name', 'phone']

    # 编辑表单里的字段分组
    fieldsets = BaseUserAdmin.fieldsets + (
        ('基本信息', {'fields': ('name', 'department', 'position', 'phone')}),
        ('头像', {'fields': ('avatar',)}),
    )