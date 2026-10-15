from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.db import transaction

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


class EmailAuthenticationForm(AuthenticationForm):
    """Login form: asks for an email, and tells an applicant whose
    account isn't active yet why, instead of a generic "wrong password"."""

    username = UsernameField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            inactive_user = self._inactive_user_with_correct_password()
            if inactive_user is None:
                raise
            join_request = getattr(inactive_user, "join_request", None)
            if join_request and join_request.is_pending:
                raise forms.ValidationError(
                    "Thanks for applying! Your application is still being reviewed - "
                    "you'll be able to log in once an officer approves it.",
                    code="pending",
                )
            raise forms.ValidationError(
                "This account isn't active. Please contact us if you think that's a mistake.",
                code="inactive",
            )

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


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ["title", "description", "category", "file", "visibility"]
        widgets = {
            "description": forms.TextInput(),
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
