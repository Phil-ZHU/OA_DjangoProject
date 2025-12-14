from django.db import models
from django.utils import timezone

class Holiday(models.Model):
    """节假日"""
    name = models.CharField('名称', max_length=50)
    date = models.DateField('日期', unique=True)

    def __str__(self):
        return f'{self.name}({self.date})'


class Shift(models.Model):
    """班次"""
    name = models.CharField('班次名', max_length=30)
    on_duty = models.TimeField('上班打卡时间')
    off_duty = models.TimeField('下班打卡时间')
    allow_early = models.PositiveSmallIntegerField('允许提前分钟', default=30)
    allow_late = models.PositiveSmallIntegerField('允许晚到分钟', default=30)

    def __str__(self):
        return self.name

class Punch(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    date = models.DateField('打卡日期', default=timezone.now)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    punch_in = models.DateTimeField('上班打卡', null=True, blank=True)
    punch_out = models.DateTimeField('下班打卡', null=True, blank=True)
    state_choices = [
        ('ok', '正常'),
        ('late', '迟到'),
        ('early', '早退'),
        ('lack', '缺卡'),
        ('out', '外勤'),
    ]
    state = models.CharField('结果', max_length=10, choices=state_choices, default='lack')
    remark = models.CharField('备注', max_length=200, blank=True)
    gps = models.CharField('GPS', max_length=50, blank=True)  # "lat,lng"

    class Meta:
        unique_together = ('user', 'date')