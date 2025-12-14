from django.core.paginator import Paginator
from django.db.models import Q,Count
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from users.models import User
from oasystem.models import Dept
from oasystem.utils import dept_as_tree
import xlrd
from django.db import transaction
import uuid
from oasystem.models import Config
from django.utils import timezone
from datetime import datetime
from attendance.models import Punch
from approval.models import Leave,ApprovalNode
import csv
from django.http import HttpResponse
from users.models import User
from django.views.decorators.http import require_POST
def user_list(request):
    kw = request.GET.get('kw', '')
    dept_id = request.GET.get('dept')
    users = User.objects.all().order_by('id')
    if kw:
        users = users.filter(
            Q(username__icontains=kw) | Q(name__icontains=kw))
    if dept_id and dept_id.isdigit():
        users = users.filter(department__in=
            Dept.objects.get(id=dept_id)\
               .get_descendants(include_self=True))  # 后面给 Dept 加方法

    cfg = Config.objects.first()
    page_size = cfg.page_size if cfg else 10  # 兜底默认值10
    paginator = Paginator(users, page_size)

    page = request.GET.get('page')
    users = paginator.get_page(page)
    dept_tree = dept_as_tree()          # 工具函数
    return render(request, 'system/user_list.html', locals())
def user_edit(request, pk):
    """ pk 不存在就新建，存在就直接用，绝不重复插入 """
    defaults = {
        'username': f'u{uuid.uuid4().hex[:8]}',  # 保证唯一
        'name': f'临时用户{pk}',
        'department': '',
        'position': '',
        'phone': '',
    }
    user, created = User.objects.get_or_create(pk=pk, defaults=defaults)
    # 新建时设置密码
    if created:
        user.set_password('123456')
        user.save()

    cfg = Config.objects.first()          # 读配置表（确保有默认行）
    if cfg is None:                       # 兜底：没配置就放过
        cfg = Config()

    if request.method == 'POST':
        user.name = request.POST.get('name', '')
        user.department = request.POST.get('department', '')
        user.position = request.POST.get('position', '')
        user.phone = request.POST.get('phone', '')

        avatar = request.FILES.get('avatar')
        if avatar:
            # 1. 大小
            max_size = getattr(cfg, 'avatar_max_size', 512)  # KB
            if avatar.size > max_size * 1024:
                messages.error(request, f'头像大小不能超过 {max_size} KB')
                return render(request, 'system/user_form.html', {'user': user})

            # 2. 后缀
            allow_ext = getattr(cfg, 'avatar_ext', 'jpg,png,gif')
            ext = avatar.name.rsplit('.', 1)[-1].lower()
            if ext not in [e.strip().lower() for e in allow_ext.split(',')]:
                messages.error(request, f'头像格式只允许：{allow_ext}')
                return render(request, 'system/user_form.html', {'user': user})

            # 校验通过才赋值
            user.avatar = avatar

        user.save()
        return redirect('oasystem:user_list')

    return render(request, 'system/user_form.html', {'user': user})

def user_del(request, pk):
    """ 删除后永远回到列表页 """
    User.objects.filter(pk=pk).delete()
    messages.success(request, '已删除')
    return redirect('oasystem:user_list')



def user_import(request):
    if request.method == 'POST':
        file = request.FILES['file']
        wb = xlrd.open_workbook(file_contents=file.read())
        sheet = wb.sheet_by_index(0)
        success, skip = 0, 0
        with transaction.atomic():
            for r in range(1, sheet.nrows):
                row = sheet.row_values(r)
                if len(row) < 6: continue
                username, name, dept, pos, phone, pwd = [str(v).strip() for v in row[:6]]
                if User.objects.filter(username=username).exists():
                    skip += 1; continue
                User.objects.create_user(
                    username=username, password=pwd,
                    name=name, department=dept, position=pos, phone=phone)
                success += 1
        messages.success(request, f'导入完成：成功 {success}，跳过 {skip}')
        return redirect('oasystem:user_list')
    return render(request, 'system/user_import.html')

def org_chart(request):
    """组织树图"""
    roots = Dept.objects.filter(parent=None).prefetch_related('leader')
    return render(request, 'system/org_chart.html', {'roots': roots})

@require_POST  # 保留装饰器，确保仅POST请求
def change_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    new_status = request.POST.get('status')
    # 简单合法性校验
    if new_status in [v for v, _ in User.STATUS_CHOICES]:
        user.status = new_status
        # 补充原逻辑：正式员工自动填充入职日期
        if new_status == 'formal' and not user.entry_date:
            user.entry_date = timezone.now().date()
        user.save()
        messages.success(request, '状态已更新')
    else:
        messages.error(request, '无效状态值')
    return redirect('oasystem:user_list')


# oasystem/views.py
from django.core.paginator import Paginator
from django.db.models import Q,Count
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from users.models import User
from oasystem.models import Dept
from oasystem.utils import dept_as_tree
import xlrd
from django.db import transaction
import uuid
from oasystem.models import Config
from django.utils import timezone
from datetime import datetime  # 新增导入
from attendance.models import Punch
from approval.models import Leave,ApprovalNode
import csv
from django.http import HttpResponse
from users.models import User
from django.views.decorators.http import require_POST

# 其他函数保留不变...

def dashboard(request):
    today = timezone.now().date()

    # 出勤率
    total_staff = User.objects.filter(is_active=True).count()
    punch_cnt = Punch.objects.filter(date=today, state='ok').count()
    attendance_rate = round(punch_cnt / total_staff * 100, 1) if total_staff else 0

    # 修复：本月请假统计（精准时区筛选）
    # 计算本月第一天 00:00:00（带时区）
    month_first = timezone.make_aware(
        datetime.combine(today.replace(day=1), datetime.min.time())
    )
    # 计算下月第一天 00:00:00（带时区）
    if month_first.month == 12:
        next_month = timezone.make_aware(
            datetime(month_first.year + 1, 1, 1, 0, 0, 0)
        )
    else:
        next_month = timezone.make_aware(
            datetime(month_first.year, month_first.month + 1, 1, 0, 0, 0)
        )

    # 修复：筛选条件 + 包含 draft 状态（可选，根据实际需求）
    leave_stats = Leave.objects.filter(
        start__gte=month_first,
        start__lt=next_month,
        state__in=['running', 'done', 'draft']  # 包含草稿，确保有数据
    ).values('leave_type').annotate(cnt=Count('id'))

    # 转换请假类型为中文（匹配模型中的 type_choices）
    leave_type_names = {
        'sick': '病假',
        'annual': '年假',
        'affair': '事假',
        'marriage': '婚假',
        'maternity': '产假',
        'other': '其他'
    }

    # 格式化数据并计算总数
    formatted_leave_stats = []
    total_leaves = 0

    for stat in leave_stats:
        leave_type = stat['leave_type']
        cnt = stat['cnt']
        total_leaves += cnt

        formatted_leave_stats.append({
            'leave_type': leave_type_names.get(leave_type, leave_type),
            'original_type': leave_type,
            'cnt': cnt
        })

    # 计算百分比
    for stat in formatted_leave_stats:
        if total_leaves > 0:
            stat['percentage'] = round((stat['cnt'] / total_leaves) * 100, 1)
        else:
            stat['percentage'] = 0

    # 待办审批数量
    user_roles = []

    # 从position字段获取角色
    if hasattr(request.user, 'position') and request.user.position:
        user_roles.append(request.user.position)

    # 从用户组获取角色
    if request.user.groups.exists():
        user_roles.extend(list(request.user.groups.values_list('name', flat=True)))

    if user_roles:
        pending = ApprovalNode.objects.filter(
            role__in=user_roles,
            approver__isnull=True
        ).count()
    else:
        pending = 0

    # 今日请假人数
    today_leave_users = Leave.objects.filter(
        start__date__lte=today,
        end__date__gte=today,
        state__in=['running', 'done']
    ).values('applicant').distinct()

    today_leaves = today_leave_users.count()

    # 本周数据
    week_start = today - timezone.timedelta(days=today.weekday())
    week_punch_users = Punch.objects.filter(
        date__gte=week_start,
        state='ok'
    ).values('user').distinct()

    week_punch = week_punch_users.count()

    # 获取最新的请假申请
    latest_leaves = Leave.objects.filter(
        state__in=['running', 'done', 'draft']  # 包含草稿，确保有数据
    ).select_related('applicant').order_by('-create_time')[:5]

    # 为请假单添加显示信息（修复：使用模型的 state_choices）
    for leave in latest_leaves:
        # 修复：使用模型的 type_choices/state_choices 映射
        leave.leave_type_display = dict(Leave.type_choices).get(leave.leave_type, leave.leave_type)
        leave.state_display = dict(Leave.state_choices).get(leave.state, leave.state)
        # 兼容 duration_hours_display
        leave.duration_hours_display = leave.duration_hours if hasattr(leave, 'duration_hours') else 0

    context = {
        'attendance_rate': attendance_rate,
        'leave_stats': formatted_leave_stats,
        'total_leaves': total_leaves,
        'pending': pending,
        'total_staff': total_staff,
        'punch_cnt': punch_cnt,
        'today_leaves': today_leaves,
        'week_punch': week_punch,
        'today': today,
        'latest_leaves': latest_leaves,
    }

    return render(request, 'system/dashboard.html', context)

def export_users(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'
    writer = csv.writer(response)
    writer.writerow(['工号', '姓名', '部门', '职位', '状态'])
    for u in User.objects.all():
        writer.writerow([u.username, u.name, u.department, u.position, u.get_status_display()])
    return response