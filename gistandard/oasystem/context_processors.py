from .utils import build_menu_tree

def menu(request):
    if request.user.is_authenticated:
        return {'MENU_TREE': build_menu_tree(request.user)}
    return {'MENU_TREE': []}