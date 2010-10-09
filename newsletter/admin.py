from newsletter.models import Newsletter, NewsletterAdmin, NewsletterJob, NewsletterMail, NewsletterLink

from django.contrib import admin
from django.http import HttpResponseRedirect, HttpResponse

import threading

class NewsletterLinkInline(admin.TabularInline):
    model = NewsletterLink
    readonly_fields = ('link_hash', 'click_count')
    max_num = 0
    can_delete = False

def send_job(modeladmin, request, queryset):
    class NewsletterSender(threading.Thread):
        """Thread to scan all Folders"""
        def run(self):
            for obj in queryset:
                obj.send()
    
    s=NewsletterSender()
    s.start()
send_job.short_description = "Deploy"

class NewsletterJobAdmin(admin.ModelAdmin):
    actions = (send_job,)
    date_hierarchy = 'date_deliver_start'
    list_display = ('newsletter', 'status', 'total_mails', 'delivery_status', 'viewed',)
    list_filter   = ('status', 'newsletter',)
    fields = ('newsletter', 'status', 'total_mails', 'delivery_status', 'viewed', 'date_deliver_start', 'date_deliver_finished',)
    readonly_fields = ('status', 'total_mails', 'delivery_status', 'viewed', 'date_deliver_start', 'date_deliver_finished',)


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('firstname', 'surname', 'company', 'location', 'email', 'language', 'done',)
    list_filter   = ('language', 'groups', 'done',)
    readonly_fields = ('email_hash', 'done',)
    

admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(NewsletterJob,NewsletterJobAdmin)
admin.site.register(NewsletterMail)
