from django import template
register = template.Library()

@register.filter('get_from_key')
def get_from_key(dict, key):
    if dict[key]:
        return '<br>'.join(dict[key])
    else:
        return "X"


@register.filter('get_from_key_mobile')
def get_from_key_mobile(dict, key):
    if key in dict:
        return dict[key].replace(',', "<br>")
    elif key == "etc":
        return ""
    else:
        return "X"