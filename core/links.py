import re

from django.urls import NoReverseMatch, reverse

# Link fields across this app (Card.link, InfoPanel.link,
# NavigationItem.url, and the Organization button/join URLs) can point
# at a page on this site, an uploaded file, or somewhere off-site:
#
#   - "core:events"                 -> an internal Django URL name,
#                                      resolved with reverse() so the
#                                      href always matches whatever
#                                      core/urls.py currently defines -
#                                      no hand-typed path to drift out
#                                      of sync with it (which is how a
#                                      Card ended up pointing at
#                                      "/events/" while urls.py only
#                                      defined "events").
#   - "resource:scholarship-application" -> an uploaded Resource
#                                      (core.models.Resource), looked
#                                      up by its slug and resolved to
#                                      that file's download URL. Lets
#                                      any link field point straight at
#                                      an admin-uploaded file without
#                                      bespoke per-page lookup code.
#   - "https://...", "mailto:...", "tel:..." -> off-site, stored and
#                                      used exactly as typed.

_ABSOLUTE_LINK_RE = re.compile(r"^(https?:)?//")
_NON_PAGE_SCHEMES = ("mailto:", "tel:")
_RESOURCE_PREFIX = "resource:"


def is_absolute_link(value):
    """True if `value` should be used exactly as typed rather than
    treated as a Django URL name - an off-site address, a protocol-
    relative //host/path link, or a mailto:/tel: link."""
    return bool(value) and (
        bool(_ABSOLUTE_LINK_RE.match(value)) or value.startswith(_NON_PAGE_SCHEMES)
    )


def _find_resource(slug):
    # Deferred import: core.models imports link_error from this module,
    # so importing core.models at module level here would be circular.
    from core.models import Resource

    return Resource.objects.filter(slug=slug, is_enabled=True).first()


def resolve_link(value):
    """Turn a stored link value into an href.

    Falls back to the raw value if it doesn't resolve, so one bad link
    degrades to a dead link instead of crashing the whole page -
    `link_error` is what should have caught that in the admin already.
    """
    if not value:
        return ""
    if is_absolute_link(value):
        return value
    if value.startswith(_RESOURCE_PREFIX):
        resource = _find_resource(value[len(_RESOURCE_PREFIX):])
        return resource.file.url if resource else value
    try:
        return reverse(value)
    except NoReverseMatch:
        return value


def link_error(value):
    """Return an error message if `value` is neither a usable off-site
    link, an uploaded resource that actually exists, nor a Django URL
    name that actually resolves, else None.

    Meant to be called from a model's clean() so a bad link is caught
    in the admin at save time, instead of silently 404ing for a site
    visitor later.
    """
    if not value or is_absolute_link(value):
        return None

    if value.startswith(_RESOURCE_PREFIX):
        slug = value[len(_RESOURCE_PREFIX):]
        if _find_resource(slug) is None:
            return (
                f'"{value}" doesn\'t match any uploaded, enabled file. '
                f'Check the Resource\'s slug (Resources in the admin).'
            )
        return None

    try:
        reverse(value)
    except NoReverseMatch:
        return (
            f'"{value}" is not a valid link. For an internal page, use '
            f'its URL name (e.g. "core:events"). For an uploaded file, '
            f'use "resource:<slug>". For an off-site link, start it '
            f'with "https://", "mailto:", or "tel:".'
        )
    return None
