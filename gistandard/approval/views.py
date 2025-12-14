# approval/views.py
import uuid
import datetime
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from approval.models import Leave, FlowTpl, ApprovalNode
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@login_required
def leave_create(request):
    print(f"DEBUG: leave_create view called. Method: {request.method}")
    print(f"DEBUG: User: {request.user}")

    if request.method == 'POST':
        print("DEBUG: Processing POST request")
        print(f"DEBUG: POST data: {request.POST}")

        try:
            # 获取请假单的ContentType
            leave_content_type = ContentType.objects.get(app_label='approval', model='leave')
            print(f"DEBUG: ContentType found: {leave_content_type}")

            # 查找对应的流程模板
            tpl = FlowTpl.objects.filter(content_type=leave_content_type).first()
            if not tpl:
                print("DEBUG: No flow template found, creating default...")
                # 如果没有流程模板，创建一个简单的默认模板
                tpl = FlowTpl.objects.create(
                    name='请假流程',
                    content_type=leave_content_type,
                    nodes=[{"role": "部门经理", "seq": 1}, {"role": "人事经理", "seq": 2}]
                )
                print(f"DEBUG: Created default flow template: {tpl}")

            # 处理时间格式转换
            start_str = request.POST.get('start')
            end_str = request.POST.get('end')
            print(f"DEBUG: start_str: {start_str}, end_str: {end_str}")

            if not start_str or not end_str:
                print("DEBUG: Start or end time is empty")
                messages.error(request, '开始时间和结束时间不能为空')
                return render(request, 'approval/leave_form.html')

            # 转换为datetime对象 - 使用正确的格式，不带时区
            try:
                # 格式：2025-12-14T09:00
                start_time = datetime.datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
                end_time = datetime.datetime.strptime(end_str, '%Y-%m-%dT%H:%M')
                print(f"DEBUG: Parsed times - start: {start_time}, end: {end_time}")
            except ValueError as e:
                print(f"DEBUG: Time parsing error: {e}")
                messages.error(request, f'时间格式错误，请使用正确的格式：{str(e)}')
                return render(request, 'approval/leave_form.html')

            # 注意：不要转换为带时区的时间
            # 因为 USE_TZ = False，数据库不支持时区感知的时间
            # start_time = timezone.make_aware(start_time)  # 注释掉这行
            # end_time = timezone.make_aware(end_time)      # 注释掉这行
            print(f"DEBUG: Using naive datetime - start: {start_time}, end: {end_time}")

            # 验证结束时间晚于开始时间
            if end_time <= start_time:
                print("DEBUG: End time is not later than start time")
                messages.error(request, '结束时间必须晚于开始时间')
                return render(request, 'approval/leave_form.html')

            # 验证请假时间是否在合理范围内
            if (end_time - start_time).days > 30:
                print("DEBUG: Leave duration exceeds 30 days")
                messages.error(request, '单次请假不能超过30天')
                return render(request, 'approval/leave_form.html')

            # 生成单号
            sn = timezone.now().strftime('%Y%m%d%H%M%S') + str(uuid.uuid4())[:4]
            print(f"DEBUG: Generated SN: {sn}")

            # 获取其他表单数据
            leave_type = request.POST.get('type', 'other')
            reason = request.POST.get('reason', '')
            print(f"DEBUG: Leave type: {leave_type}, Reason length: {len(reason)}")

            # 创建请假单 - 使用原生datetime（不带时区）
            leave = Leave.objects.create(
                sn=sn,
                applicant=request.user,
                leave_type=leave_type,
                start=start_time,  # 原生datetime，不带时区
                end=end_time,  # 原生datetime，不带时区
                reason=reason,
                state='running'
            )
            print(f"DEBUG: Leave created with ID: {leave.id}, SN: {leave.sn}")

            # 创建审批节点
            if hasattr(tpl, 'nodes') and tpl.nodes:
                print(f"DEBUG: Flow template has {len(tpl.nodes)} nodes")
                for idx, node_data in enumerate(tpl.nodes):
                    ApprovalNode.objects.create(
                        apply_sn=sn,
                        role=node_data.get('role', f'审批人{idx + 1}'),
                        seq=node_data.get('seq', idx + 1)
                    )
                    print(f"DEBUG: Created approval node {idx + 1}: {node_data}")
            else:
                # 如果没有节点配置，创建默认审批节点
                print("DEBUG: No nodes in flow template, creating default node")
                ApprovalNode.objects.create(
                    apply_sn=sn,
                    role='部门经理',
                    seq=1
                )

            print("DEBUG: Success! Redirecting to leave_list")
            messages.success(request, '请假申请已提交，等待审批')
            return redirect('approval:leave_list')

        except Exception as e:
            print(f"DEBUG: Exception in leave_create: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'提交失败：{str(e)}')
            return render(request, 'approval/leave_form.html')
    else:
        # GET请求，显示表单
        print("DEBUG: Handling GET request, showing form")
        return render(request, 'approval/leave_form.html')


@login_required
def leave_list(request):
    """显示当前用户的请假列表"""
    leaves = Leave.objects.filter(applicant=request.user).order_by('-create_time')

    context = {
        'leaves': leaves,
    }
    return render(request, 'approval/leave_list.html', context)


@login_required
def pending_list(request):
    """显示当前用户需要审批的请假单"""
    # 这里需要根据用户的角色来过滤
    # 假设用户有一个role字段，或者通过Group来判断
    user_roles = request.user.groups.values_list('name', flat=True)

    # 查找当前用户角色对应的待审批节点
    pending_nodes = ApprovalNode.objects.filter(
        role__in=user_roles,
        approver__isnull=True
    ).order_by('seq')

    # 获取对应的请假单号
    pending_sns = pending_nodes.values_list('apply_sn', flat=True).distinct()

    # 获取请假单详情
    pending_leaves = Leave.objects.filter(
        sn__in=pending_sns,
        state='running'
    )

    context = {
        'pending_leaves': pending_leaves,
        'pending_nodes': pending_nodes,
    }
    return render(request, 'approval/pending_list.html', context)


@login_required
def leave_create(request):
    print(f"DEBUG: leave_create view called. Method: {request.method}")
    print(f"DEBUG: User: {request.user}")

    if request.method == 'POST':
        print("DEBUG: Processing POST request")
        print(f"DEBUG: POST data: {request.POST}")

        try:
            # 获取请假单的ContentType
            leave_content_type = ContentType.objects.get(app_label='approval', model='leave')
            print(f"DEBUG: ContentType found: {leave_content_type}")

            # 查找对应的流程模板
            tpl = FlowTpl.objects.filter(content_type=leave_content_type).first()
            if not tpl:
                print("DEBUG: No flow template found, creating default...")
                # 如果没有流程模板，创建一个简单的默认模板
                tpl = FlowTpl.objects.create(
                    name='请假流程',
                    content_type=leave_content_type,
                    nodes=[{"role": "部门经理", "seq": 1}, {"role": "人事经理", "seq": 2}]
                )
                print(f"DEBUG: Created default flow template: {tpl}")

            # 处理时间格式转换
            start_str = request.POST.get('start')
            end_str = request.POST.get('end')
            print(f"DEBUG: start_str: {start_str}, end_str: {end_str}")

            if not start_str or not end_str:
                print("DEBUG: Start or end time is empty")
                messages.error(request, '开始时间和结束时间不能为空')
                return render(request, 'approval/leave_form.html')

            # 转换为datetime对象
            try:
                # 尝试解析ISO格式
                start_time = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_time = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                print(f"DEBUG: Parsed times - start: {start_time}, end: {end_time}")
            except ValueError:
                # 尝试其他时间格式
                try:
                    start_time = datetime.datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
                    end_time = datetime.datetime.strptime(end_str, '%Y-%m-%dT%H:%M')
                    print(f"DEBUG: Parsed with alternative format")
                except ValueError as e:
                    print(f"DEBUG: Time parsing error: {e}")
                    messages.error(request, f'时间格式错误：{str(e)}')
                    return render(request, 'approval/leave_form.html')

            # 转换为带时区的时间
            start_time = timezone.make_aware(start_time)
            end_time = timezone.make_aware(end_time)
            print(f"DEBUG: Timezone aware - start: {start_time}, end: {end_time}")

            # 验证结束时间晚于开始时间
            if end_time <= start_time:
                print("DEBUG: End time is not later than start time")
                messages.error(request, '结束时间必须晚于开始时间')
                return render(request, 'approval/leave_form.html')

            # 验证请假时间是否在合理范围内
            if (end_time - start_time).days > 30:
                print("DEBUG: Leave duration exceeds 30 days")
                messages.error(request, '单次请假不能超过30天')
                return render(request, 'approval/leave_form.html')

            # 生成单号
            sn = timezone.now().strftime('%Y%m%d%H%M%S') + str(uuid.uuid4())[:4]
            print(f"DEBUG: Generated SN: {sn}")

            # 获取其他表单数据
            leave_type = request.POST.get('type', 'other')
            reason = request.POST.get('reason', '')
            print(f"DEBUG: Leave type: {leave_type}, Reason length: {len(reason)}")

            # 创建请假单 - 状态设置为 running
            leave = Leave.objects.create(
                sn=sn,
                applicant=request.user,
                leave_type=leave_type,
                start=start_time,
                end=end_time,
                reason=reason,
                state='running'
            )
            print(f"DEBUG: Leave created with ID: {leave.id}, SN: {leave.sn}")

            # 检查流程模板是否有节点配置
            if hasattr(tpl, 'nodes') and tpl.nodes:
                print(f"DEBUG: Flow template has {len(tpl.nodes)} nodes")
                # 实例化审批节点
                for idx, node_data in enumerate(tpl.nodes):
                    ApprovalNode.objects.create(
                        apply_sn=sn,
                        role=node_data.get('role', ''),
                        seq=node_data.get('seq', idx + 1)
                    )
                    print(f"DEBUG: Created approval node {idx + 1}: {node_data}")
            else:
                # 如果没有配置节点，直接完成
                print("DEBUG: No nodes in flow template, marking as done")
                leave.state = 'done'
                leave.save()
                messages.success(request, '请假申请已自动完成（无审批流程）')
                return redirect('approval:leave_list')

            print("DEBUG: Redirecting to leave_list")
            messages.success(request, '请假申请已提交，等待审批')
            return redirect('approval:leave_list')

        except Exception as e:
            print(f"DEBUG: Exception in leave_create: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'提交失败：{str(e)}')
            return render(request, 'approval/leave_form.html')
    else:
        # GET请求，显示表单
        print("DEBUG: Handling GET request, showing form")
        return render(request, 'approval/leave_form.html')


@login_required
def leave_detail(request, sn):
    """查看请假单详情"""
    try:
        leave = Leave.objects.get(sn=sn)
    except Leave.DoesNotExist:
        messages.error(request, '请假单不存在')
        return redirect('approval:leave_list')

    # 权限检查：申请人或审批人可以查看
    if leave.applicant != request.user:
        # 检查用户是否有审批权限
        user_roles = []
        if hasattr(request.user, 'position') and request.user.position:
            user_roles.append(request.user.position)
        if request.user.groups.exists():
            user_roles.extend(list(request.user.groups.values_list('name', flat=True)))

        # 检查是否有审批节点
        is_approver = ApprovalNode.objects.filter(
            apply_sn=sn,
            role__in=user_roles
        ).exists()

        if not is_approver and not request.user.is_staff:
            messages.error(request, '无权查看此请假单')
            return redirect('approval:leave_list')

    # 获取审批节点记录
    approval_nodes = ApprovalNode.objects.filter(apply_sn=sn).order_by('seq')

    # 添加显示信息
    leave.state_display = dict(Leave.state_choices).get(leave.state, leave.state)
    leave.leave_type_display = dict(Leave.type_choices).get(leave.leave_type, leave.leave_type)

    # 计算时长
    leave.duration_hours_display = leave.duration_hours

    context = {
        'leave': leave,
        'approval_nodes': approval_nodes,
    }
    return render(request, 'approval/leave_detail.html', context)

@login_required
def approve_action(request, sn):
    """审批操作"""
    # 查找当前用户可以审批的节点
    user_roles = request.user.groups.values_list('name', flat=True)

    try:
        node = ApprovalNode.objects.get(
            apply_sn=sn,
            role__in=user_roles,
            approver__isnull=True
        )
    except ApprovalNode.DoesNotExist:
        messages.error(request, '没有找到待审批的节点或您无权审批')
        return redirect('approval:pending_list')

    action = request.POST.get('action')
    comment = request.POST.get('comment', '')

    # 更新审批节点
    node.approver = request.user
    node.action = action
    node.comment = comment
    node.save()

    # 获取请假单
    leave = get_object_or_404(Leave, sn=sn)

    if action == 'reject':
        # 驳回
        leave.state = 'reject'
        leave.save()
        messages.success(request, '已驳回请假申请')
    else:
        # 同意
        # 检查是否还有待审批的节点
        remaining_nodes = ApprovalNode.objects.filter(
            apply_sn=sn,
            approver__isnull=True
        ).exists()

        if not remaining_nodes:
            # 所有节点都审批完成
            leave.state = 'done'
            leave.save()
            messages.success(request, '请假申请已审批完成')
        else:
            messages.success(request, '已同意，等待下一步审批')

    return redirect('approval:pending_list')


@login_required
def pending_count_api(request):
    """API接口：获取当前用户的待办审批数量"""
    try:
        # 获取用户的角色
        user_roles = []

        # 从position字段获取角色
        if hasattr(request.user, 'position') and request.user.position:
            user_roles.append(request.user.position)

        # 从用户组获取角色
        if request.user.groups.exists():
            user_roles.extend(list(request.user.groups.values_list('name', flat=True)))

        # 计算待办数量
        if user_roles:
            count = ApprovalNode.objects.filter(
                role__in=user_roles,
                approver__isnull=True
            ).count()
        else:
            count = 0

        return JsonResponse({
            'success': True,
            'count': count,
            'user': request.user.username,
            'roles': user_roles
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'count': 0
        }, status=500)

