from django import forms

from .models import ContactMessage, Resource, ResourceCategory


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
