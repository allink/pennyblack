from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext_lazy as _

from feincms.admin import editor

import threading

from pennyblack.models import Newsletter, Job, Mail, Link, Sender
from pennyblack import settings
from pennyblack.forms import JobAdminForm

class LinkInline(admin.TabularInline):
    model = Link
    max_num = 0
    can_delete = False
    readonly_fields = ('link_hash', 'click_count',)


class MailInline(admin.TabularInline):
    model = Mail
    max_num = 0
    fields = ('get_email',)
    readonly_fields = ('get_email',)

class NewsletterAdmin(editor.ItemEditor, admin.ModelAdmin):
    list_display = ('__unicode__', 'subject', 'newsletter_type')
    show_on_top = ('subject', 'sender', 'reply_email',)
    raw_id_fields = ('header_image',)
    fields = ('name', 'newsletter_type', 'sender', 'subject', 'reply_email', 'language', 'utm_source', 'utm_medium', 'template_key', 'header_image', 'header_url', 'site')
    exclude = ('header_url_replaced',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('newsletter_type',)
        return self.readonly_fields

    def queryset(self, request):
        return self.model.objects.active()

    def get_urls(self):
        urls = super(NewsletterAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^(?P<newsletter_id>\d+)/preview/$', 'pennyblack.views.preview')
        )
        return my_urls + urls
    

class JobAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_deliver_start'
    actions = None
    list_display = ('newsletter', 'group_object', 'status', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_created')
    list_filter   = ('status', 'newsletter',)
    fields = ('newsletter', 'collection', 'status', 'group_object', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_deliver_start', 'date_deliver_finished',)
    readonly_fields = ('collection', 'status', 'group_object', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_deliver_start', 'date_deliver_finished',)    
    inlines = (LinkInline, MailInline,)
    form = JobAdminForm
    
    def get_readonly_fields(self, request, obj):
        if obj.status in settings.JOB_STATUS_CAN_EDIT:
            return self.readonly_fields
        else:
            return self.readonly_fields + ('newsletter',)
        
    def statistics_view(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        return render_to_response('admin/pennyblack/job/statistics.html',{'object':obj})
    
    def change_view(self, request, object_id, extra_context={}):
        obj = get_object_or_404(self.model, pk=object_id)
        extra_context['can_send']=obj.can_send
        return super(JobAdmin, self).change_view(request, object_id, extra_context)

    def send_newsletter_view(self,request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        if request.method == 'POST' and request.POST.has_key("_send"):
            obj.status = 11
            obj.save()
            self.message_user(request, _("Newsletter has been marked for delivery."))
        return HttpResponseRedirect(reverse('admin:%s_%s_changelist' %(self.model._meta.app_label,  self.model._meta.module_name)))

    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        if request.POST.has_key("_send_prepare"):
            context = {'object':obj}
            context.update(csrf(request))
            return render_to_response(
                'admin/pennyblack/job/send_confirmation.html', context)
        return super(JobAdmin,self).response_change(request, obj)

    def get_urls(self):
        urls = super(JobAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        my_urls = patterns('',
            url(r'^(?P<object_id>\d+)/statistics/$', self.admin_site.admin_view(self.statistics_view), name='%s_%s_statistics' % info),
            url(r'^(?P<object_id>\d+)/send/$', self.admin_site.admin_view(self.send_newsletter_view), name=('%s_%s_send' % info)),
        )
        return my_urls + urls

class SenderAdmin(admin.ModelAdmin):
    list_display = ('email', 'name',)
    fields = ('email', 'name', 'imap_username', 'imap_password', 'imap_server', 'imap_port', 'get_bounce_emails', 'spf_result',)
    readonly_fields = ('spf_result',)

admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(Job,JobAdmin)
admin.site.register(Sender,SenderAdmin)