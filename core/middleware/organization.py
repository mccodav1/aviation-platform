from core.utils import get_organization


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update this to determine which organization to load
        request.organization = get_organization()

        response = self.get_response(request)

        return response