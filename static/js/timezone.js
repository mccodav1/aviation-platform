// Reports the browser's timezone to the server via a cookie (read by
// core/middleware/timezone.py), so times render in the visitor's own
// zone. The very first page is rendered in the server's fallback zone
// before the cookie exists - if that differs from the browser's, reload
// once. The reload only happens after confirming the cookie actually
// stuck, so a browser blocking cookies can't loop.
(function () {
    try {
        var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (!tz) return;
        var entry = "tz=" + encodeURIComponent(tz);
        var hasCookie = function () {
            return document.cookie.split("; ").indexOf(entry) !== -1;
        };
        if (hasCookie()) return;
        document.cookie = entry + "; path=/; max-age=31536000; SameSite=Lax";
        if (hasCookie() && document.documentElement.dataset.timezone !== tz) {
            window.location.reload();
        }
    } catch (e) {
        // Leave the server's fallback timezone in place.
    }
})();
