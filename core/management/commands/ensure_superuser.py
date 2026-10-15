import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

# The same variable names Django's own `createsuperuser --noinput` reads.
USERNAME_VAR = "DJANGO_SUPERUSER_USERNAME"
PASSWORD_VAR = "DJANGO_SUPERUSER_PASSWORD"


class Command(BaseCommand):
    help = (
        f"Creates a superuser from {USERNAME_VAR}/{PASSWORD_VAR} if no user "
        "with that username exists yet. Run on every container start (see "
        "docker/entrypoint.sh). An existing user is left untouched - its "
        "password is never reset from the environment, so changing it in "
        "/admin sticks."
    )

    def handle(self, *args, **options):
        username = os.environ.get(USERNAME_VAR, "").strip()
        password = os.environ.get(PASSWORD_VAR, "")
        if not username or not password:
            raise CommandError(f"{USERNAME_VAR} and {PASSWORD_VAR} must both be set.")

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser '{username}' already exists - leaving it as is.")
            return

        User.objects.create_superuser(username=username, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'."))
