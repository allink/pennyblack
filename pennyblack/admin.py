from pennyblack.models import Newsletter, NewsletterJob, Mail, Link, Sender
from pennyblack import settings

from django.contrib import admin
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.conf.urls.defaults import patterns
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render_to_response


from feincms.admin import editor

import threading

class LinkInline(admin.TabularInline):
    model = Link
    #readonly_fields = ('link_hash', 'click_count',)
    max_num = 0
    can_delete = False
    readonly_fields = ('link_hash', 'click_count',)


class MailInline(admin.TabularInline):
    model = Mail
    max_num = 0
    fields = ('get_email',)
    readonly_fields = ('get_email',)

class NewsletterAdmin(editor.ItemEditor, admin.ModelAdmin):
    list_display = ('__unicode__', 'subject',)
    show_on_top = ('subject', 'sender', 'reply_email')
    raw_id_fields = ('header_image',)
    fields = ('name', 'sender', 'subject', 'reply_email', 'language', 'utm_source', 'utm_medium', 'template_key', 'header_image', 'header_url')

    def queryset(self, request):
        qs = super(NewsletterAdmin, self).queryset(request)
        return qs.filter(active=True)

    def get_urls(self):
        urls = super(NewsletterAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^(?P<newsletter_id>\d+)/preview/$', 'pennyblack.views.preview')
        )
        return my_urls + urls
    

class NewsletterJobAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_deliver_start'
    actions = None
    list_display = ('newsletter', 'status', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_created')
    list_filter   = ('status', 'newsletter',)
    fields = ('newsletter', 'collection', 'status', 'group_object', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_deliver_start', 'date_deliver_finished',)
    readonly_fields = ('collection', 'status', 'group_object', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_deliver_start', 'date_deliver_finished',)    
    inlines = (LinkInline, MailInline,)
    
    def get_readonly_fields(self, request, obj):
        if obj.status in settings.JOB_STATUS_CAN_EDIT:
            return self.readonly_fields
        else:
            return self.readonly_fields + ('newsletter',)
        
    def statistics_view(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        return render_to_response('admin/pennyblack/newsletterjob/statistics.html',{'object':obj})
    
    def change_view(self, request, object_id, extra_context={}):
        obj = get_object_or_404(self.model, pk=object_id)
        extra_context['can_send']=obj.can_send
        return super(NewsletterJobAdmin, self).change_view(request, object_id, extra_context)

    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        if request.POST.has_key("_send"):
            obj.status = 11
            obj.save()
            self.message_user(request, _("Newsletter has been marked for delivery."))
        return super(NewsletterJobAdmin,self).response_change(request, obj)

    def get_urls(self):
        urls = super(NewsletterJobAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^(?P<object_id>\d+)/statistics/$', self.admin_site.admin_view(self.statistics_view))
        )
        return my_urls + urls

class SenderAdmin(admin.ModelAdmin):
    list_display = ('email', 'name',)
    fields = ('email', 'name', 'pop_username', 'pop_password', 'pop_server', 'pop_port', 'spf_result',)
    readonly_fields = ('spf_result',)

admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(NewsletterJob,NewsletterJobAdmin)
admin.site.register(Sender,SenderAdmin)