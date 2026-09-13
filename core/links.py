import re

from django.urls import NoReverseMatch, reverse

# Link fields across this app (Card.link, InfoPanel.link,
# NavigationItem.url, and the Organization button/join URLs) can point
# either at a page on this site or somewhere off-site. An internal link
# is stored as a Django URL name (e.g. "core:events") and resolved with
# reverse() at render time, so the href always matches whatever
# core/urls.py currently defines - there's no hand-typed path left to
# drift out of sync with it (which is how a Card ended up pointing at
# "/events/" while urls.py only defined "events"). Off-site links are
# stored, and used, exactly as typed.

_ABSOLUTE_LINK_RE = re.compile(r"^(https?:)?//")
_NON_PAGE_SCHEMES = ("mailto:", "tel:")


def is_absolute_link(value):
    """True if `value` should be used exactly as typed rather than
    treated as a Django URL name - an off-site address, a protocol-
    relative //host/path link, or a mailto:/tel: link."""
    return bool(value) and (
        bool(_ABSOLUTE_LINK_RE.match(value)) or value.startswith(_NON_PAGE_SCHEMES)
    )


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
    try:
        return reverse(value)
    except NoReverseMatch:
        return value


def link_error(value):
    """Return an error message if `value` is neither a usable off-site
    link nor a Django URL name that actually resolves, else None.

    Meant to be called from a model's clean() so a bad link is caught
    in the admin at save time, instead of silently 404ing for a site
    visitor later.
    """
    if not value or is_absolute_link(value):
        return None
    try:
        reverse(value)
    except NoReverseMatch:
        return (
            f'"{value}" is not a valid link. For an internal page, use '
            f'its URL name (e.g. "core:events"). For an off-site link, '
            f'start it with "https://", "mailto:", or "tel:".'
        )
    return None
