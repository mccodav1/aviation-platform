from django import forms

from .models import Meeting
from .widgets import PrivateClearableFileInput


class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ["title", "starts_at", "location", "description", "is_cancelled"]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class MeetingAgendaForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ["agenda"]
        widgets = {"agenda": PrivateClearableFileInput}


class MeetingMinutesForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ["minutes"]
        widgets = {"minutes": PrivateClearableFileInput}
