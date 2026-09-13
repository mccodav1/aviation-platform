from django import template

from core.links import resolve_link as _resolve_link

register = template.Library()


@register.filter(name="resolve_link")
def resolve_link(value):
    """Turn a stored Card/InfoPanel/NavigationItem/Organization link
    value into an href - see core.links.resolve_link for what that
    means for internal (URL name) vs. off-site links."""
    return _resolve_link(value)
