from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from users.models import User
from oasystem.models import Menu, SubMenu, Dept

class Command(BaseCommand):
    help = '初始化 OA 基础角色 & 菜单'

    def handle(self, *args, **options):
        # 1. 权限
        user_ct = ContentType.objects.get_for_model(User)
        dept_ct = ContentType.objects.get_for_model(Dept)
        menu_ct = ContentType.objects.get_for_model(Menu)

        perms = [
            ('can_view_user', '员工_查看', user_ct),
            ('can_edit_user', '员工_编辑', user_ct),
            ('can_view_dept', '部门_查看', dept_ct),
            ('can_edit_dept', '部门_编辑', dept_ct),
            ('can_view_menu', '菜单_查看', menu_ct),
        ]
        for codename, name, ct in perms:
            Permission.objects.get_or_create(
                codename=codename, name=name, content_type=ct)
        # 2、权限

        Permission.objects.get_or_create(
            codename='can_edit_user_btn', name='员工_列表编辑按钮', content_type=user_ct)
        Permission.objects.get_or_create(
            codename='can_del_user_btn', name='员工_列表删除按钮', content_type=user_ct)
        # 3. 角色
        hr_group, _ = Group.objects.get_or_create(name='人事专员')
        hr_group.permissions.set(Permission.objects.filter(
            codename__in=['can_view_user', 'can_edit_user',
                          'can_view_dept', 'can_edit_dept']))

        normal_group, _ = Group.objects.get_or_create(name='普通员工')
        normal_group.permissions.set(Permission.objects.filter(
            codename__in=['can_view_user', 'can_view_dept']))

        self.stdout.write(self.style.SUCCESS('角色与权限已初始化'))