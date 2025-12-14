from django.shortcuts import render, redirect
from django.contrib.auth import login,logout
from django.contrib import messages
from .models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import Group
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from .decorators import no_cache  # 导入新创建的装饰器

@csrf_protect
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username','').strip()

        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        name = request.POST.get('name')
        department = request.POST.get('department')
        phone = request.POST.get('phone')
        # ===== ① 非空校验（新增）=====
        if not username:
            messages.error(request, '工号不能为空')
            return render(request, 'users/register.html')


        if password != password2:
            messages.error(request, '两次密码不一致')
            return render(request, 'users/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, '工号已存在')
            return render(request, 'users/register.html')

        user = User.objects.create_user(
            username=username,
            password=password,
            name=name,
            department=department,
            phone=phone,
            is_active = True  # 强制激活用户（默认True，显式设置更安全）
        )
        try:
            # 关联"普通员工"组（需先执行 init_auth 命令创建该组）
            normal_group = Group.objects.get(name='普通员工')
            user.groups.add(normal_group)
        except Group.DoesNotExist:
            # 若未初始化权限组，临时提示（后续需执行 python manage.py init_auth）
            messages.warning(request, '权限组未初始化，需联系管理员配置！')

        login(request, user)          # 注册完直接登录
        messages.success(request, '注册成功！')
        return redirect('index')      # 后面再建
    return render(request, 'users/register.html')

class MyLoginView(LoginView):
    template_name = 'users/login.html'
    redirect_authenticated_user = True  # 已登录用户直接跳转
    # 添加CSRF保护装饰器
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """登录成功后跳转的URL"""
        # 检查是否有next参数
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        # 返回settings中配置的LOGIN_REDIRECT_URL
        return self.get_redirect_url() or super().get_success_url()

    def form_valid(self, form):
        """登录成功时的处理"""
        response = super().form_valid(form)
        # 可以在这里添加自定义逻辑
        messages.success(self.request, f'欢迎回来，{self.request.user.name or self.request.user.username}!')
        return response

    def form_invalid(self, form):
        """登录失败时的处理"""
        username = self.request.POST.get('username', '')
        # 检查用户是否存在
        user_exists = User.objects.filter(username=username).exists()

        if not user_exists:
            messages.error(self.request, '用户不存在，请检查工号是否正确')
        else:
            # 检查用户是否激活
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    messages.error(self.request, '账户未激活，请联系管理员')
                else:
                    messages.error(self.request, '密码错误，请重试')
            except User.DoesNotExist:
                messages.error(self.request, '用户不存在，请检查工号是否正确')

            # 调用父类方法显示表单错误
        return super().form_invalid(form)
@login_required
@no_cache  # 添加此行
def index(request):
    return render(request, 'users/index.html')


# 修改退出登录视图
@no_cache
def logout_view(request):
    # 强制清空会话（彻底销毁登录状态）
    logout(request)
    request.session.flush()  # 关键：清空所有会话数据
    request.session.clear_expired()
    messages.success(request, '已成功退出登录')
    # 重定向时添加随机参数，防止缓存
    response = redirect(f"{reverse('users:login')}?t={datetime.now().timestamp()}")
    # 再次强化缓存控制
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

