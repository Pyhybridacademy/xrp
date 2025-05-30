from main.models import SiteSettings

def site_settings(request):
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    return {'site_settings': settings}