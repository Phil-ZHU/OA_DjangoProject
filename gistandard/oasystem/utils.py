from oasystem.models import Menu
from oasystem.models import Dept
def build_menu_tree(user):
    """返回可见菜单树"""
    tree = []
    # 只取一级菜单
    for m in Menu.objects.all():
        # 一级权限判断
        if m.permission and not user.has_perm(
                f'{m.permission.content_type.app_label}.'
                f'{m.permission.codename}'):
            continue
        # 二级
        subs = []
        for sub in m.subs.all():
            if sub.permission and not user.has_perm(
                    f'{sub.permission.content_type.app_label}.'
                    f'{sub.permission.codename}'):
                continue
            subs.append({'name': sub.name, 'url': sub.url})
        if subs or not m.permission:   # 无权限限制的一级菜单也显示
            tree.append({
                'name': m.name,
                'icon': m.icon,
                'subs': subs
            })
    return tree

def dept_as_tree():
    """返回嵌套列表，模板里递归用"""
    roots = Dept.objects.filter(parent=None)
    def build(node):
        return {'id': node.id, 'name': node.name,
                'children': [build(c) for c in Dept.objects.filter(parent=node)]}
    return [build(r) for r in roots]

def get_report_line(user):
    """从用户部门向上找负责人，返回 [最高层, ..., 直接上级]"""
    line = []
    if not user.department_id:                       # 部门字段存的是字符串，这里演示逻辑
        return line
    try:
        dept = Dept.objects.get(name=user.department)
    except Dept.DoesNotExist:
        return line
    while dept:
        if dept.leader:
            line.insert(0, dept.leader)   # 越靠前级别越高
        dept = dept.parent
    return line