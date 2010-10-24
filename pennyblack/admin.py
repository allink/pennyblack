from pennyblack.models import Newsletter, NewsletterJob, Mail, Link, Sender

from django.contrib import admin
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

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
    raw_id_fields = []
    fields = ('name', 'sender', 'subject', 'reply_email', 'language', 'utm_source', 'utm_medium', 'template_key')

    def queryset(self, request):
          qs = super(NewsletterAdmin, self).queryset(request)
          return qs.filter(active=True)
    

class NewsletterJobAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_deliver_start'
    actions = None
    list_display = ('newsletter', 'status', 'total_mails', 'delivery_status', 'viewed', 'date_created')
    list_filter   = ('status', 'newsletter',)
    fields = ('newsletter', 'status', 'group_object', 'total_mails', 'delivery_status', 'viewed', 'date_deliver_start', 'date_deliver_finished',)
    readonly_fields = ('status', 'group_object', 'total_mails', 'delivery_status', 'viewed', 'date_deliver_start', 'date_deliver_finished',)    
    inlines = (LinkInline, MailInline,)
    
    def get_readonly_fields(self, request, obj):
        if obj.status == 1:
            return self.readonly_fields
        else:
            return self.readonly_fields + ('newsletter',)
        
    def send_newsletter(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        obj.send()
        return HttpResponseRedirect(reverse('admin:pennyblack_newsletterjob_change', args=(obj.id,)))
    
    def change_view(self, request, object_id, extra_context={}):
        obj = get_object_or_404(self.model, pk=object_id)
        extra_context['can_send']=obj.can_send
        return super(NewsletterJobAdmin, self).change_view(request, object_id, extra_context)

    def get_urls(self):
        from django.conf.urls.defaults import patterns
        urls = super(NewsletterJobAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^(?P<object_id>\d+)/send/$', self.admin_site.admin_view(self.send_newsletter))
        )
        return my_urls + urls

class SenderAdmin(admin.ModelAdmin):
    list_display = ('email', 'name',)
    fields = ('email', 'name', 'pop_username', 'pop_password', 'pop_server', 'pop_port', 'spf_result',)
    readonly_fields = ('spf_result',)

admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(NewsletterJob,NewsletterJobAdmin)
admin.site.register(Sender,SenderAdmin)