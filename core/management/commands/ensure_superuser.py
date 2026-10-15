import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

# The same variable names Django's own `createsuperuser --noinput` reads
# (DJANGO_SUPERUSER_<USERNAME_FIELD>) now that accounts log in by email.
EMAIL_VAR = "DJANGO_SUPERUSER_EMAIL"
PASSWORD_VAR = "DJANGO_SUPERUSER_PASSWORD"


class Command(BaseCommand):
    help = (
        f"Creates a superuser from {EMAIL_VAR}/{PASSWORD_VAR} if no account "
        "with that email exists yet. Run on every container start (see "
        "docker/entrypoint.sh). An existing account is left untouched - its "
        "password is never reset from the environment, so changing it in "
        "/admin sticks."
    )

    def handle(self, *args, **options):
        email = os.environ.get(EMAIL_VAR, "").strip()
        password = os.environ.get(PASSWORD_VAR, "")
        if not email or not password:
            raise CommandError(f"{EMAIL_VAR} and {PASSWORD_VAR} must both be set.")

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f"Superuser '{email}' already exists - leaving it as is.")
            return

        user = User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser '{user.email}'."))
