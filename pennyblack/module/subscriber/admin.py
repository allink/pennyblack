from django.contrib import admin

from pennyblack.module.subscriber.models import NewsletterSubscriber,\
    NewsletterSubscriberAdmin, SubscriberGroup, SubscriberGroupAdmin

admin.site.register(NewsletterSubscriber, NewsletterSubscriberAdmin)
admin.site.register(SubscriberGroup, SubscriberGroupAdmin)