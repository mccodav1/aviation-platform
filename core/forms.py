import math
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.db import transaction

from . import throttle
from .widgets import PrivateClearableFileInput

from .models import ContactMessage, JoinRequest, Resource, ResourceCategory, User


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._organization = organization

    def save(self, commit=True):
        contact_message = super().save(commit=False)
        contact_message.organization = self._organization
        if commit:
            contact_message.save()
        return contact_message


class JoinRequestForm(forms.ModelForm):
    """The Join page's application. Saving it also creates the
    applicant's account - inactive until an officer approves - with the
    password they choose here, so there's nothing to set up afterwards."""

    password1 = forms.CharField(
        label="Choose a password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="You'll use this with your email to log in once you're approved.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = JoinRequest
        fields = [
            "first_name", "last_name", "email", "password1", "password2",
            "phone", "pilot_status", "message",
        ]
        labels = {
            "email": "Email (this will be your login)",
            "phone": "Phone (optional)",
            "pilot_status": "Where are you in aviation?",
            "message": "Anything you'd like us to know? (optional)",
        }
        widgets = {
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "message": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "What you fly, what you're hoping to get out of the club, how you heard about us...",
            }),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._organization = organization

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. If you've already "
                "applied, an officer will be in touch - otherwise, try logging in."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords don't match.")
        elif password1:
            # Runs AUTH_PASSWORD_VALIDATORS, including "too similar to
            # your name/email", against the account about to be created.
            candidate = User(
                email=cleaned_data.get("email", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
            )
            try:
                password_validation.validate_password(password1, candidate)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        join_request = super().save(commit=False)
        join_request.organization = self._organization
        join_request.user = User.objects.create_user(
            email=join_request.email,
            password=self.cleaned_data["password1"],
            first_name=join_request.first_name,
            last_name=join_request.last_name,
            is_active=False,
        )
        join_request.save()
        return join_request


class ThrottledLoginMixin:
    """Login throttling for an AuthenticationForm (see core/throttle.py).
    Used by both the site's login form and the admin's, so /admin/login/
    isn't a way around it. A locked-out IP/email pair is refused before
    the password is even checked."""

    def clean(self):
        email = self.cleaned_data.get("username") or ""
        password = self.cleaned_data.get("password")
        attempted = bool(email and password)

        if attempted:
            remaining = throttle.lockout_remaining(self.request, email)
            if remaining:
                raise self._locked_out_error(remaining)

        try:
            cleaned_data = super().clean()
        except forms.ValidationError:
            if not attempted:
                raise
            inactive_error = self._inactive_account_error()
            if inactive_error:
                # The right password for an account that just isn't
                # active - not a guess, so it doesn't count as a failure.
                raise inactive_error
            if throttle.record_failure(self.request, email):
                raise self._locked_out_error(timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES))
            raise

        throttle.clear_failures(self.request, email)
        return cleaned_data

    def _locked_out_error(self, remaining):
        minutes = max(1, math.ceil(remaining.total_seconds() / 60))
        return forms.ValidationError(
            f"Too many failed login attempts. Please wait {minutes} minute{'s' if minutes != 1 else ''} "
            "and try again, or contact us if you're locked out.",
            code="locked_out",
        )

    def _inactive_account_error(self):
        """An error explaining why a correct-password login isn't
        allowed, or None to fall through to the generic error."""
        return None

    def _inactive_user_with_correct_password(self):
        # Only reveals an account's status to someone who knows its
        # password - a wrong password still gets the generic error.
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not email or not password:
            return None
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if user and user.check_password(password):
            return user
        return None


class EmailAuthenticationForm(ThrottledLoginMixin, AuthenticationForm):
    """The site's login form: asks for an email, and tells an applicant
    whose account isn't active yet why, instead of a generic "wrong
    password"."""

    username = UsernameField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    def _inactive_account_error(self):
        inactive_user = self._inactive_user_with_correct_password()
        if inactive_user is None:
            return None
        join_request = getattr(inactive_user, "join_request", None)
        if join_request and join_request.is_pending:
            return forms.ValidationError(
                "Thanks for applying! Your application is still being reviewed - "
                "you'll be able to log in once an officer approves it.",
                code="pending",
            )
        return forms.ValidationError(
            "This account isn't active. Please contact us if you think that's a mistake.",
            code="inactive",
        )


class ThrottledAdminAuthenticationForm(ThrottledLoginMixin, AdminAuthenticationForm):
    """/admin/login/ with the same throttling as the site's login."""

    def _inactive_account_error(self):
        # The admin login keeps Django's generic error, but a correct
        # password for an inactive account still isn't counted as a guess.
        if self._inactive_user_with_correct_password():
            return forms.ValidationError(
                self.error_messages["invalid_login"],
                code="invalid_login",
                params={"username": self.username_field.verbose_name},
            )
        return None


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ["title", "description", "category", "file", "visibility"]
        widgets = {
            "description": forms.TextInput(),
            # Shows the current file's name when editing, without asking
            # private storage for a URL (which it refuses on purpose).
            "file": PrivateClearableFileInput,
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._organization = organization
        self.fields["category"].queryset = ResourceCategory.objects.filter(
            organization=organization, is_enabled=True,
        )
        self.fields["category"].empty_label = "-- choose a category --"
        # The model field's help_text explains PROTECT semantics for
        # deleting a category in the admin - not relevant when adding a
        # resource, so it's overridden here rather than in the model.
        self.fields["category"].help_text = ""

    def save(self, commit=True):
        resource = super().save(commit=False)
        resource.organization = self._organization
        if commit:
            resource.save()
        return resource
