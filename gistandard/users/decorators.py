# users/decorators.py
from django.http import HttpResponse
from functools import wraps

def no_cache(view_func):
    """禁用页面缓存的装饰器"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        # 设置响应头禁用缓存
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Vary'] = '*'  # 确保每次请求都重新获取
        return response
    return _wrapped_view