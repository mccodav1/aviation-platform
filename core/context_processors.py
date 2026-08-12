# core/context_processors.py
from core.utils import get_organization


def organization(request):
    return {
        "organization": get_organization()
    }


