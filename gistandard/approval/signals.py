# approval/signals.py
import logging
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from approval.models import ApprovalNode, Leave
from users.models import User

logger = logging.getLogger('oa')

# ------------------  缓存清理  ------------------
def _clear_all_dashboard_cache():
    """清掉所有用户仪表盘缓存"""
    for u in User.objects.filter(is_active=True):
        cache.delete(f'dashboard_{u.id}')

@receiver(post_save, sender=ApprovalNode)
@receiver(post_delete, sender=ApprovalNode)
def clear_on_node_change(sender, **kwargs):
    _clear_all_dashboard_cache()

@receiver(post_save, sender=Leave)
@receiver(post_delete, sender=Leave)
def clear_on_leave_change(sender, **kwargs):
    _clear_all_dashboard_cache()

# ------------------  邮件通知  ------------------
@receiver(post_save, sender=ApprovalNode)
def node_save(sender, instance, created, **kwargs):
    """
    新节点生成（待审批）时发邮件
    支持「指定人」或「角色」两种模式
    """
    # 仅处理新建的、未指定审批人的节点
    if created and not instance.approver:
        subject = f'OA 审批：单号 {instance.apply_sn}'
        message = f'您有一个【{instance.role or "指定审批"}】待审批，请登录系统处理。'

        # 1. 修复：instance.user → instance.approver（ApprovalNode的审批人字段是approver）
        # 补充：判断approver是否存在（避免空值）
        if instance.approver and instance.approver.email:
            recipient_list = [instance.approver.email]
        # 2. 否则按角色找人（示例：role=人事专员）
        else:
            users = User.objects.filter(
                groups__name=instance.role
            ).exclude(email='').distinct()
            recipient_list = [u.email for u in users]

        if recipient_list:
            try:
                # 修复：补充默认发件人（避免settings.DEFAULT_FROM_EMAIL不存在报错）
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@example.com')
                send_mail(
                    subject,
                    message,
                    from_email,  # 改用兼容写法
                    recipient_list,
                    fail_silently=False,
                )
                logger.info(f'审批邮件已发送 → {recipient_list}')
            except Exception as e:
                logger.error(f'审批邮件发送失败: {e}')