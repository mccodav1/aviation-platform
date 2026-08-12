# core/context_processors.py

from core.models import Organization

def organization(request):
    return {
        "organization": getattr(request, "organization", None)
    }