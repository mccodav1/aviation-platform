from django import forms

from .models import Event, EventAttachment
from core.widgets import PrivateClearableFileInput


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


class EventAttachmentForm(forms.ModelForm):
    class Meta:
        model = EventAttachment
        fields = ["title", "file"]
        labels = {"title": "Name", "file": "File"}
        help_texts = {"title": 'What it is, e.g. "Treasurer\'s report" or "Fly-out route".'}
        widgets = {"file": PrivateClearableFileInput}

