from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from attendance.models import Punch, Shift
from datetime import datetime


# 修复：统一为带时区时间比较
def punch_in(request):
    """上班打卡"""
    today = timezone.now().date()
    punch = Punch.objects.get(user=request.user, date=today)
    if punch.punch_in:
        messages.error(request, '已打过上班卡')
        return redirect('attendance:punch_page')
    punch.punch_in = timezone.now()

    # 关键修复：为 std 添加时区（转为 offset-aware）
    std_naive = datetime.combine(today, punch.shift.on_duty)  # 原无时区时间
    std = timezone.make_aware(std_naive)  # 转为带时区（Asia/Shanghai）

    # 现在类型一致，可正常比较
    if punch.punch_in > std + timezone.timedelta(minutes=punch.shift.allow_late):
        punch.state = 'late'
    else:
        punch.state = 'ok'
    punch.save()
    messages.success(request, '上班打卡成功')
    return redirect('attendance:punch_page')


def punch_out(request):
    """下班打卡"""
    today = timezone.now().date()
    punch = Punch.objects.get(user=request.user, date=today)
    if punch.punch_out:
        messages.error(request, '已打过下班卡')
        return redirect('attendance:punch_page')
    punch.punch_out = timezone.now()

    # 关键修复：为 std 添加时区（转为 offset-aware）
    std_naive = datetime.combine(today, punch.shift.off_duty)  # 原无时区时间
    std = timezone.make_aware(std_naive)  # 转为带时区（Asia/Shanghai）

    # 现在类型一致，可正常比较
    if punch.punch_out < std - timezone.timedelta(minutes=punch.shift.allow_early):
        punch.state = 'early'
    punch.save()
    messages.success(request, '下班打卡成功')
    return redirect('attendance:punch_page')


# 添加安全获取班次的函数
def get_or_create_shift():
    """安全获取班次，不存在则创建"""
    shift, created = Shift.objects.get_or_create(
        name="标准班",
        defaults={
            'on_duty': datetime.strptime('09:00:00', '%H:%M:%S').time(),  # 确保是 time 类型
            'off_duty': datetime.strptime('18:00:00', '%H:%M:%S').time(),
            'allow_early': 30,
            'allow_late': 30
        }
    )
    return shift


# 保留登录装饰器，确保只有登录用户可打卡
@login_required
def punch_page(request):
    today = timezone.now().date()
    shift = get_or_create_shift()  # 使用安全函数

    # 确保 shift 不为 None
    punch, created = Punch.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={'shift': shift}  # shift 必须提供
    )

    return render(request, 'attendance/punch.html', {'punch': punch})