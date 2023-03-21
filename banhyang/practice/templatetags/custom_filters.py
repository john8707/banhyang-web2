from django import template
register = template.Library()

@register.filter('get_from_key')
def get_from_key(dict, key):
    if key in dict:
        return dict[key]
    elif key == "etc":
        return ""
    else:
        return "X"