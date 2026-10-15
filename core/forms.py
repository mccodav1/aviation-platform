from django import forms

from .models import ContactMessage, JoinRequest, Resource, ResourceCategory


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
    class Meta:
        model = JoinRequest
        fields = ["name", "email", "phone", "pilot_status", "message"]
        labels = {
            "name": "Your name",
            "phone": "Phone (optional)",
            "pilot_status": "Where are you in aviation?",
            "message": "Anything you'd like us to know? (optional)",
        }
        widgets = {
            "message": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "What you fly, what you're hoping to get out of the club, how you heard about us...",
            }),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._organization = organization

    def save(self, commit=True):
        join_request = super().save(commit=False)
        join_request.organization = self._organization
        if commit:
            join_request.save()
        return join_request


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
