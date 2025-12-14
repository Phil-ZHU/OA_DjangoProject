from django.contrib import admin
from oasystem.models import Menu, SubMenu, Dept
from .models import Config
class SubMenuInline(admin.TabularInline):
    model = SubMenu
    extra = 1

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort', 'permission']
    inlines = [SubMenuInline]

@admin.register(Dept)
class DeptAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_filter = ['parent']
    search_fields = ['name']

@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False  # 禁止新增
    def has_delete_permission(self, request, obj=None):
        return False