"""Login throttling: failed attempts are tracked per (IP address, email)
pair, and LOGIN_FAILURE_LIMIT failures lock that pair out for
LOGIN_LOCKOUT_MINUTES. Used by both login forms (the site's and the
admin's - see ThrottledLoginMixin in core/forms.py)."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import LoginLockout


def client_ip(request):
    # nginx appends the address it actually received to X-Forwarded-For
    # (proxy_add_x_forwarded_for), so the last entry is the real client -
    # anything before it came from the client and could be forged.
    # gunicorn is only reachable through nginx (see SECURE_PROXY_SSL_HEADER
    # in settings), so the header itself can't be spoofed past nginx.
    # Without nginx (runserver), there's no header and REMOTE_ADDR is it.
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


def _key(request, email):
    return {"email": email.strip().lower(), "ip_address": client_ip(request)}


def lockout_remaining(request, email):
    """How long this IP is still locked out for this email, or None."""
    lockout = LoginLockout.objects.filter(**_key(request, email)).first()
    if lockout and lockout.is_locked:
        return lockout.locked_until - timezone.now()
    return None


def record_failure(request, email):
    """Counts a failed attempt; returns True if it just triggered a lockout."""
    now = timezone.now()
    window = timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
    lockout, _ = LoginLockout.objects.get_or_create(
        **_key(request, email), defaults={"last_failure_at": now},
    )
    # Start counting afresh once a lockout has run out, or if the last
    # failure was long enough ago that this isn't the same burst.
    if (lockout.locked_until and lockout.locked_until <= now) or lockout.last_failure_at < now - window:
        lockout.failed_attempts = 0
        lockout.locked_until = None

    lockout.failed_attempts += 1
    lockout.last_failure_at = now
    if lockout.failed_attempts >= settings.LOGIN_FAILURE_LIMIT:
        lockout.locked_until = now + window
    lockout.save()
    return lockout.locked_until is not None


def clear_failures(request, email):
    LoginLockout.objects.filter(**_key(request, email)).delete()


def unlock(email):
    """Clears every lockout for an account, from every IP - the Users
    page's Unlock button."""
    LoginLockout.objects.filter(email=email.strip().lower()).delete()


def locked_emails():
    """Emails with at least one active lockout, for listing users."""
    return set(
        LoginLockout.objects.filter(locked_until__gt=timezone.now()).values_list("email", flat=True)
    )
