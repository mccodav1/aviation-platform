from core.models import Organization


def get_organization():
    return Organization.objects.first()