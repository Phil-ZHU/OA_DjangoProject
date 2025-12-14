import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User

class LogMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # 只记录增删改
        if request.method not in ('POST', 'PUT', 'DELETE'): return
        request._start = time.time()

    def process_template_response(self, request, response):
        if hasattr(request, '_start') and request.user.is_authenticated:
            cost = int((time.time() - request._start)*1000)
            # 简单写文件，后期可改模型
            with open('oa_op.log', 'a', encoding='utf8') as f:
                f.write(f'{request.user.username} | {request.method} | '
                        f'{request.path} | {cost}ms\n')
        return response