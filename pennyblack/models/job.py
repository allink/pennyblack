from django import forms
from django.contrib import admin
from django.conf.urls.defaults import patterns, url
from django.contrib.contenttypes import generic
from django.core import mail
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from pennyblack import settings

import datetime

#-----------------------------------------------------------------------------
# Job
#-----------------------------------------------------------------------------
class Job(models.Model):
    """A bunch of participants wich receive a newsletter"""
    newsletter = models.ForeignKey('pennyblack.Newsletter', related_name="jobs", null=True)
    status = models.IntegerField(choices=settings.JOB_STATUS, default=1)
    date_created = models.DateTimeField(verbose_name="Created", default=datetime.datetime.now())
    date_deliver_start = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Started", default=None)
    date_deliver_finished = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Finished", default=None)

    content_type = models.ForeignKey('contenttypes.ContentType', null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    group_object = generic.GenericForeignKey('content_type', 'object_id')
    collection = models.TextField(blank=True)
    
    #ga tracking
    utm_campaign = models.SlugField(verbose_name="Utm Campaign")
    
    
    class Meta:
        ordering = ('date_created',)
        verbose_name = "Newsletter delivery task"
        verbose_name_plural = "Newsletter delivery tasks"
        app_label = 'pennyblack'
        
        
    def __unicode__(self):
        return (self.newsletter.subject if self.newsletter is not None else "unasigned Job")
    
    def delete(self, *args, **kwargs):
        if self.newsletter.active == False:
            self.newsletter.delete()
        super(Job, self).delete(*args, **kwargs)
    
    def count_mails_total(self):
        return self.mails.count()
    count_mails_total.short_description = '# of mails'
    
    def count_mails_sent(self):
        return self.mails.filter(sent=True).count()
    count_mails_sent.short_description = '# of mails sent'

    @property
    def percentage_mails_sent(self):
        if self.count_mails_total() == 0:
            return 0
        return round(float(self.count_mails_sent())/float(self.count_mails_total()) * 100)
    
    def count_mails_viewed(self):
        return self.mails.exclude(viewed=None).count()
    count_mails_viewed.short_description = '# of views'

    @property
    def percentage_mails_viewed(self):
        if self.count_mails_total() == 0:
            return 0
        return round(float(self.count_mails_viewed())/float(self.count_mails_total()) * 100)
    
    def count_mails_bounced(self):
        return self.mails.filter(bounced=True).count()
    count_mails_bounced.short_description = '# of bounces'

    @property
    def percentage_mails_bounced(self):
        if self.count_mails_total() == 0:
            return 0
        return round(float(self.count_mails_bounced())/float(self.count_mails_total()) * 100)

    def can_send(self):
        if not self.status in settings.JOB_STATUS_CAN_SEND:
            return False
        return self.is_valid()

    def is_valid(self):
        if self.newsletter == None or not self.newsletter.is_valid():
            return False
        return True
    
    def create_mails(self, queryset):
        """
        Create mails for every NewsletterReceiverMixin in queryset.
        """
        for receiver in queryset:
            self.create_mail(receiver)
            
    def create_mail(self, receiver):
        """
        Creates a single mail. This is also used in workflow mail send process.
        """
        return self.mails.create(person=receiver)
        
    
    def add_link(self, link):
        """
        Adds a link and returns a replacement link
        """
        link = self.links.create(link_target=link)
        link.save()
        return '{{base_url}}' + reverse('pennyblack.redirect_link', kwargs={'mail_hash':'{{mail.mail_hash}}','link_hash':link.link_hash}).replace('%7B','{').replace('%7D','}')
    
    def send(self):
        self.newsletter = self.newsletter.create_snapshot()
        self.newsletter.replace_links(self)
        self.status = 21
        self.date_deliver_start = datetime.datetime.now()
        self.save()
        try:
            translation.activate(self.newsletter.language)
            connection = mail.get_connection()
            connection.open()
            for newsletter_mail in self.mails.filter(sent=False):
                connection.send_messages([newsletter_mail.get_message()])
                newsletter_mail.mark_sent()
            connection.close()
        except:
            self.status = 41
            raise
        else:
            self.status = 31
            self.date_deliver_finished = datetime.datetime.now()
        self.save()

class JobAdminForm(forms.ModelForm):
    from pennyblack.models.newsletter import Newsletter
    newsletter = forms.ModelChoiceField(queryset=Newsletter.objects.massmail())

class JobAdmin(admin.ModelAdmin):
    from pennyblack.models.link import LinkInline
    from pennyblack.models.mail import MailInline
    
    date_hierarchy = 'date_deliver_start'
    actions = None
    list_display = ('newsletter', 'group_object', 'status', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_created')
    list_filter   = ('status', 'newsletter',)
    fields = ('newsletter', 'collection', 'status', 'group_object', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_deliver_start', 'date_deliver_finished',)
    readonly_fields = ('collection', 'status', 'group_object', 'count_mails_total', 'count_mails_sent', 'count_mails_viewed', 'date_deliver_start', 'date_deliver_finished',)    
    inlines = (LinkInline, MailInline,)
    massmail_form = JobAdminForm
    
    def get_form(self, request, obj=None, **kwargs):
        if obj and obj.status in settings.JOB_STATUS_CAN_EDIT:
            kwargs['form'] = self.massmail_form
        return super(JobAdmin, self).get_form(request, obj, **kwargs)
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status in settings.JOB_STATUS_CAN_EDIT:
            return self.readonly_fields
        else:
            return self.readonly_fields + ('newsletter',)
        
    def statistics_view(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        return render_to_response('admin/pennyblack/job/statistics.html',{'object':obj})
    
    def change_view(self, request, object_id, extra_context={}):
        obj = get_object_or_404(self.model, pk=object_id)
        extra_context['can_send']=obj.can_send
        request._pennyblack_job_obj = obj # add object to request for the mail inline
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
