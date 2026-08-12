from core.models import Organization


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update this to determine which organization to load
        request.organization = Organization.objects.first()

        response = self.get_response(request)

        return response