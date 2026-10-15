import logging

# Many tests check that a page refuses access (403) or doesn't exist (404),
# and one checks a failed notification email. Django logs each of those as
# a warning with a traceback, which would bury real failures in the test
# output - so only errors are logged during tests.
for name in ("django.request", "core.views"):
    logging.getLogger(name).setLevel(logging.ERROR)
