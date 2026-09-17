from django import forms

from .models import Event
from .widgets import PrivateClearableFileInput


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["event_type", "title", "starts_at", "location", "description", "is_cancelled"]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class EventAgendaForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["agenda"]
        widgets = {"agenda": PrivateClearableFileInput}


class EventMinutesForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["minutes"]
        widgets = {"minutes": PrivateClearableFileInput}
