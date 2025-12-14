# oasystem/middleware.py
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class PreventBackAfterLogoutMiddleware(MiddlewareMixin):
    """拦截退出后回退的请求，强制验证登录状态"""

    def process_response(self, request, response):
        # 1. 对所有需要登录的页面添加严格的缓存控制头
        if hasattr(request, 'user') and not request.user.is_authenticated:
            # 禁用所有缓存
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Vary'] = '*'
        return response

    def process_request(self, request):
        # 2. 白名单：登录页、静态文件、API等无需登录的路径
        whitelist = [
            reverse('users:login'),
            '/static/',
            '/media/',
            '/favicon.ico',
            '/approval/api/pending-count/',  # 新增：待办数量API加入白名单
        ]

        # 3. 替换废弃的 request.is_ajax() → 用请求头判断AJAX
        def is_ajax(request):
            """兼容Django4.0+的AJAX判断方法"""
            return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # 4. 检查是否未登录且访问受保护页面（排除AJAX请求）
        if (not request.path.startswith(tuple(whitelist)) and
                hasattr(request, 'user') and
                not request.user.is_authenticated and
                not is_ajax(request)):  # 使用自定义的is_ajax方法
            # 强制重定向到登录页，且使用302（禁止缓存重定向）
            return HttpResponseRedirect(reverse('users:login'))