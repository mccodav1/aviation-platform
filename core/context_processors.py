# core/context_processors.py
def organization(request):
    return {
        "organization": request.organization
    }


