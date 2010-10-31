from django.conf import settings

PENNYBLACK_TINYMCE_CONFIG_URL = getattr(settings, 'TINYMCE_CONFIG_URL', 'admin/content/richtext/init.html')