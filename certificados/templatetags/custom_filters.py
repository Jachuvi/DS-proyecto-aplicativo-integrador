from django import template

register = template.Library()

@register.filter
def dict(d, key):
    return d.get(key)