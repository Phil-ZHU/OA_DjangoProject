from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    # 每个字段明确指定 verbose_name（中文）
    name = models.CharField(max_length=20, verbose_name="姓名")  # ✅ 已加
    department = models.CharField(max_length=50, verbose_name="部门", blank=True, null=True)  # ✅ 已加
    position = models.CharField(max_length=50, verbose_name="职位", blank=True, null=True)  # ✅ 已加
    phone = models.CharField(max_length=11, verbose_name="手机号", blank=True, null=True)  # ✅ 已加
    avatar = models.ImageField(upload_to='avatars/', verbose_name="头像", blank=True, null=True)  # ✅ 已加

    STATUS_CHOICES = (
        ('trial', '试用期'),
        ('formal', '正式'),
        ('intern', '实习'),
        ('resign', '离职'),
    )
    status = models.CharField('状态', max_length=10,
                              choices=STATUS_CHOICES, default='trial')
    entry_date = models.DateField('入职日期', blank=True, null=True)

    # ========== 关键修改2：显式声明 is_active 默认值（确保用户激活） ==========
    is_active = models.BooleanField('是否激活', default=True)

    def __str__(self):
        return self.name or self.username

    # 可选：给模型本身加中文名称
    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"  # 复数形式也显示“用户”（避免默认“用户s”）