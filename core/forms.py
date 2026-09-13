from django import forms

from .models import Resource, ResourceCategory


class ResourceForm(forms.ModelForm):
    # Not a model field - lets an officer type a brand new category
    # instead of picking one of the existing ones. The two are mutually
    # exclusive: clean() rejects the submission if both or neither are
    # filled in, rather than silently letting one win (see clean()).
    # field_order below pairs this with the "category" dropdown it
    # complements - a ModelForm otherwise renders declared fields like
    # this one after every Meta.fields field, which put it dead last,
    # separated from "category" by "file" and "visibility".
    new_category = forms.CharField(
        max_length=200,
        required=False,
        label="Or create a new category",
        help_text="Leave blank to use the dropdown above instead.",
    )

    field_order = ["title", "description", "category", "new_category", "file", "visibility"]

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
        self.fields["category"].required = False
        self.fields["category"].empty_label = "-- choose an existing category --"
        # The model field's help_text explains PROTECT semantics for
        # deleting a category in the admin - not relevant when adding a
        # resource, so it's overridden here rather than in the model.
        self.fields["category"].help_text = ""

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        new_category_title = cleaned_data.get("new_category", "").strip()

        if category and new_category_title:
            raise forms.ValidationError(
                "Choose an existing category or type a new one - not "
                "both. Clear whichever one you don't want to use."
            )

        if not category and not new_category_title:
            raise forms.ValidationError(
                "Choose an existing category or type a new one."
            )

        if new_category_title:
            category, _ = ResourceCategory.objects.get_or_create(
                organization=self._organization,
                title=new_category_title,
            )
            cleaned_data["category"] = category

        return cleaned_data

    def save(self, commit=True):
        resource = super().save(commit=False)
        resource.organization = self._organization
        resource.category = self.cleaned_data["category"]
        if commit:
            resource.save()
        return resource
