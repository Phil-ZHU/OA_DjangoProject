from django import template
register = template.Library()

@register.inclusion_tag('system/dept_tree.html')
def dept_tree(nodes, dept_id):
    return {'nodes': nodes, 'dept_id': dept_id}