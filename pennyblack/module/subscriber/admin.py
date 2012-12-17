from django.contrib import admin

from pennyblack.module.subscriber.models import NewsletterSubscriber,\
    NewsletterSubscriberAdmin, SubscriberGroup, SubscriberGroupAdmin

admin.site.register(NewsletterSubscriber, NewsletterSubscriberAdmin)
admin.site.register(SubscriberGroup, SubscriberGroupAdmin)

try:
    from admin_import.options import add_import
except ImportError, e:
    if not str(e) == 'No module named admin_import.options':
        raise
else:
    from django.conf import settings as django_settings
    if 'admin_import' in django_settings.INSTALLED_APPS:
        add_import(NewsletterSubscriberAdmin, add_button=True)
