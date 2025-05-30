from .models import SiteSettings

def site_settings(request):
    """
    Context processor for main app - only applies to non-admin URLs
    """
    # Skip if this is an admin request (let custom_admin handle it)
    if request.path.startswith('/admin/'):
        return {}
    
    try:
        settings = SiteSettings.objects.first()
        if not settings:
            settings = SiteSettings.objects.create()
        
        return {
            'site_settings': settings,
            'site_name': settings.site_name,
            'site_logo': settings.logo,
            'contact_email': settings.contact_email,
            'contact_phone': settings.contact_phone,
            'live_chat_enabled': settings.live_chat_enabled,
            'live_chat_script_url': settings.live_chat_script_url,
        }
    except Exception as e:
        return {
            'site_settings': None,
            'site_name': 'Trading Platform',
            'site_logo': None,
            'contact_email': '',
            'contact_phone': '',
            'live_chat_enabled': False,
            'live_chat_script_url': '',
        }
