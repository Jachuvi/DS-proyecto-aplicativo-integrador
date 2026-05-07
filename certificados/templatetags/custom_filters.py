from django import template

register = template.Library()

@register.filter
def dict_lookup(d, key):
    if hasattr(d, 'get') and callable(getattr(d, 'get')):
        return d.get(key)
    return None

@register.filter(name='get_item')
def get_item(d, key):
    if hasattr(d, 'get') and callable(getattr(d, 'get')):
        return d.get(key)
    return None