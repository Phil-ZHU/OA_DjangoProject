from django.db import models
from django.contrib.auth.models import Permission

class Menu(models.Model):
    """一级菜单"""
    name = models.CharField('菜单名', max_length=30)
    icon = models.CharField('图标类', max_length=30, blank=True)
    sort = models.PositiveIntegerField('排序', default=1)
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, blank=True, null=True,
        help_text='拥有该权限才可见；空则所有登录用户可见')

    class Meta:
        ordering = ['sort']
        verbose_name = '一级菜单'
        verbose_name_plural = '一级菜单'

    def __str__(self):
        return self.name


class SubMenu(models.Model):
    """二级菜单"""
    parent = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='subs')
    name = models.CharField('子菜单名', max_length=30)
    url = models.CharField('URL 名', max_length=100, help_text='Django url name，如 users:index')
    sort = models.PositiveIntegerField('排序', default=1)
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ['sort']
        verbose_name = '二级菜单'
        verbose_name_plural = '二级菜单'

    def __str__(self):
        return f'{self.parent}-{self.name}'


class Dept(models.Model):
    name = models.CharField('部门名称', max_length=50)
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True, verbose_name='上级部门')

    leader = models.ForeignKey('users.User', on_delete=models.SET_NULL,
                               null=True, blank=True, verbose_name='部门负责人')
    def get_descendants(self, include_self=False):
        """简单递归，性能够用"""
        ids = [self.id] if include_self else []
        for child in Dept.objects.filter(parent=self):
            ids.append(child.id)
            ids.extend(child.get_descendants())
        return ids
    class Meta:
        verbose_name = '部门'
        verbose_name_plural = '部门'

    def __str__(self):
        return self.name
class Config(models.Model):
    """系统配置，singleton 表，仅 id=1 有效"""
    avatar_max_size = models.PositiveIntegerField('头像最大尺寸(KB)', default=512)
    avatar_ext = models.CharField('允许头像后缀', max_length=100, default='jpg,jpeg,png')
    page_size = models.PositiveIntegerField('默认分页条数', default=15)

    class Meta:
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @staticmethod
    def get():
        """获取唯一配置"""
        obj, _ = Config.objects.get_or_create(id=1)
        return obj

class AuditLog(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField('动作', max_length=50)
    path = models.CharField('路径', max_length=200)
    ip = models.GenericIPAddressField('IP')
    ua = models.TextField('UA', blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']