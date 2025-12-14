# oasystem/templatetags/custom_filters.py
from django import template

register = template.Library()

# 自定义除法过滤器
@register.filter(name='div')
def div(value, arg):
    """除法过滤器：value / arg，返回整数"""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0

# 自定义取模过滤器
@register.filter(name='mod')
def mod(value, arg):
    """取模过滤器：value % arg，返回余数"""
    try:
        return int(value) % int(arg)
    except (ValueError, ZeroDivisionError):
        return 0