from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

User = get_user_model()  # 使用get_user_model()更安全


class FlowTpl(models.Model):
    """流程模板"""
    name = models.CharField('流程名', max_length=50)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='适用类型'
    )
    # JSON 保存节点 [{role:'人事', seq:1}, {role:'财务', seq:2}]
    nodes = models.JSONField('节点', default=list)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '流程模板'
        verbose_name_plural = '流程模板'


class AbstractApply(models.Model):
    """所有审批单公共字段"""
    sn = models.CharField('单号', max_length=30, unique=True)
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='申请人'
    )
    state_choices = [
        ('draft', '草稿'),
        ('running', '审批中'),
        ('done', '完成'),
        ('reject', '驳回'),
    ]
    state = models.CharField('状态', max_length=10, choices=state_choices, default='draft')
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        abstract = True


class ApprovalNode(models.Model):
    """审批节点实例"""
    apply_sn = models.CharField('单号', max_length=30, db_index=True)
    role = models.CharField('审批角色', max_length=30)
    seq = models.PositiveSmallIntegerField('序号')
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='审批人'
    )
    action = models.CharField(
        '动作',
        max_length=10,
        choices=[('agree', '同意'), ('reject', '驳回')],
        blank=True
    )
    comment = models.CharField('意见', max_length=200, blank=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    def __str__(self):
        return f"{self.apply_sn}-{self.role}({self.seq})"

    class Meta:
        ordering = ['seq']
        verbose_name = '审批节点'
        verbose_name_plural = '审批节点'


class Leave(AbstractApply):
    """请假单"""
    type_choices = [
        ('sick', '病假'),
        ('annual', '年假'),
        ('affair', '事假'),
        ('marriage', '婚假'),
        ('maternity', '产假'),
        ('other', '其他'),
    ]
    leave_type = models.CharField('请假类型', max_length=10, choices=type_choices)
    start = models.DateTimeField('开始时间')
    end = models.DateTimeField('结束时间')
    reason = models.TextField('事由')

    @property
    def duration_days(self):
        """计算请假天数"""
        if self.start and self.end:
            delta = self.end - self.start
            return delta.days + 1  # 包含开始和结束当天
        return 0

    @property
    def duration_hours(self):
        """计算请假小时数（兼容dashboard视图）"""
        if self.start and self.end:
            delta = self.end - self.start
            return round(delta.total_seconds() / 3600, 1)
        return 0

    def get_duration_hours(self):
        return self.duration_hours

    def __str__(self):
        return f'{self.applicant}-{self.get_leave_type_display()} ({self.sn})'

    class Meta:
        verbose_name = '请假单'
        verbose_name_plural = '请假单'


# 如果需要报销单等其他类型
class Expense(AbstractApply):
    """报销单"""
    expense_type_choices = [
        ('travel', '差旅费'),
        ('office', '办公费'),
        ('entertainment', '招待费'),
        ('other', '其他'),
    ]
    expense_type = models.CharField('报销类型', max_length=20, choices=expense_type_choices)
    amount = models.DecimalField('金额', max_digits=10, decimal_places=2)
    description = models.TextField('描述')
    attachment = models.FileField('附件', upload_to='expenses/', blank=True, null=True)

    def __str__(self):
        return f'{self.applicant}-{self.get_expense_type_display()}-{self.amount}'

    class Meta:
        verbose_name = '报销单'
        verbose_name_plural = '报销单'