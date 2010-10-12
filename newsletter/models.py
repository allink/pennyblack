from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.utils import translation
from django.core import mail
from django.conf import settings
from django.template import loader, Context, Template
from django.contrib.sites.models import Site
from django.db.models import signals
from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

from feincms.models import Base
from feincms.management.checker import check_database_schema

import exceptions
import hashlib
import random
import sys
import datetime

      
class Newsletter(Base):
    """A newsletter with subject and content
    can contain multiple jobs with mails to send"""
    name = models.CharField(verbose_name="Name", help_text="Wird nur intern verwendet.", max_length=100)
    subject = models.CharField(verbose_name="Betreff", max_length=250)
    from_email = models.EmailField(verbose_name="Von E-Mail Adresse")
    from_name = models.CharField(verbose_name="Von Name", help_text="Wird in vielen E-Mail Clients als Von angezeit.", max_length=100)
    reply_email = models.EmailField(verbose_name="Reply-to" ,blank=True)
    
    #ga tracking
    utm_source = models.SlugField(verbose_name="Utm Source", default="newsletter")
    utm_medium = models.SlugField(verbose_name="Utm Medium", default="cpc")

    class Meta:
        ordering = ('subject',)
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"
            
    def __unicode__(self):
        return self.name
        
    # def check_links(self):
    #     """
    #     Searches al links in content sections
    #     """
    #     for content in self.content.main:
            
    
    # def get_template(self):
    #     return Template('{%% extends "newsletter/email.html" %%}{%% block newscontainer %%}%s{%% endblock %%}' % (self.content,))

signals.post_syncdb.connect(check_database_schema(Newsletter, __name__), weak=False)


class NewsletterLink(models.Model):
    newsletter = models.ForeignKey(Newsletter)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    newsletter_content = generic.GenericForeignKey('content_type', 'object_id')

    link_hash = models.CharField(max_length=32, blank=True)
    link_target = models.CharField(verbose_name="Adresse", max_length=500)
    click_count = models.IntegerField(default=0)
    
    def __unicode__(self):
        return self.link_target
    
    def save(self, **kwargs):
        if self.link_hash == u'':
            self.link_hash = hashlib.md5(str(self.id)+str(random.random())).hexdigest()
        super(NewsletterLink, self).save(**kwargs)

class NewsletterReceiverMixin(object):
    """
    Abstract baseclass for every object that can receive a newsletter
    """    
    def get_email(self):
        if hasattr(self,'email'):
            return self.email
        raise exceptions.NotImplementedError('Need a get_email implementation.')

class NewsletterJobUnitMixin(object):
    """
    Abstract baseclass for every object which can be target of a NewsletterJob
    """    
    def create_newsletter(self):
        """
        Creates a newsletter for every NewsletterReceiverMixin
        """
        job = NewsletterJob(group_object=self)
        job.save()
        job.create_mails()
        return job
    
    def get_newsletter_receivers(self):
        """
        Tries to get a queryset named client or participants bevore giving up.
        """
        queryset = getattr(self, 'clients', None)
        if queryset:
            return queryset
        queryset = getattr(self, 'participants', None)
        if queryset:
            return queryset
        raise exeptions.NotImplementedError("Didn't find any subset, you need to implement get_newsletter_receivers yourselfe.")

class NewsletterJobUnitAdmin(admin.ModelAdmin):
    change_form_template = "admin/newsletter/jobunit/change_form.html"
    
    def create_newsletter(self, request, object_id):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(self.model, pk=object_id)
        job = obj.create_newsletter()
        return HttpResponseRedirect(reverse('admin:newsletter_newsletterjob_change', args=(job.id,)))
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns
        urls = super(NewsletterJobUnitAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^(?P<object_id>\d+)/create_newsletter/$', self.admin_site.admin_view(self.create_newsletter))
        )
        return my_urls + urls
        


class NewsletterJob(models.Model):
    """A bunch of participants wich receive a newsletter"""
    newsletter = models.ForeignKey(Newsletter, related_name="jobs", null=True)
    status = models.IntegerField(choices=((1,'Draft'),(2,'Pending'),(3,'Sending'),(4,'Finished'),(5,'Error'),), default=1)
    date_deliver_start = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Started", default=None)
    date_deliver_finished = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Finished", default=None)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    group_object = generic.GenericForeignKey('content_type', 'object_id')
    
    #ga tracking
    utm_campaign = models.SlugField(verbose_name="Utm Campaign")
    
    
    class Meta:
        ordering = ('newsletter', 'status',)
        verbose_name = "Newsletter delivery task"
        verbose_name_plural = "Newsletter delivery tasks"
        
    def __unicode__(self):
        return (self.newsletter.subject if self.newsletter is not None else "unasigned NewsletterJob")
    
    def total_mails(self):
        return str(self.mails.count())
    total_mails.short_description = '# of mails'
    
    def delivery_status(self):
        return str(self.mails.filter(sent=True).count())
    delivery_status.short_description = '# of mails sent'
    
    def viewed(self):
        return str(self.mails.filter(viewed=True).count())
    viewed.short_description = '# of views'
    
    def _can_send(self):
        return True
        # return True if self.status == 1 or self.status == 5 else False
    can_send = property(_can_send)

    
    def create_mails(self):
        """
        Create mails for every NewsletterReceiverMixin in self.group_object.
        """
        if not hasattr(self.group_object, 'get_newsletter_receivers'):
            raise exceptions.NotImplementedError('Object needs to implement get_newsletter_receivers')
        for receiver in self.group_object.get_newsletter_receivers():
            self.mails.add(NewsletterMail(person=receiver))
    
    def send(self):
        if not self.can_send():
            raise exceptions.Exception('Can only send jobs in status 1 or 5')
        self.status = 3
        self.date_deliver_start = datetime.datetime.now()
        self.save()
        template = self.newsletter.get_template()
        try:
            connection = mail.get_connection()
            for newsletter_mail in self.mails.filter(sent=False):
                connection.send_messages([newsletter_mail.get_message(template, self.event, self.group)])
                newsletter_mail.mark_sent()
            connection.close()
        except:
            self.status = 5
        else:
            self.status = 4
            self.date_deliver_finished = datetime.datetime.now()
        self.save()

class NewsletterMail(models.Model):
    """
    This is a single Mail, it's part of a NewsletterJob
    """
    viewed = models.BooleanField(default=False)
    sent = models.BooleanField(default=False)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    person = generic.GenericForeignKey('content_type', 'object_id')
    job = models.ForeignKey(NewsletterJob, related_name="mails")
    mail_hash = models.CharField(max_length=32, blank=True)
    
    def __unicode__(self):
        return '%s to %s' % (self.job, self.person,)
        
    def save(self, **kwargs):
        if self.mail_hash == u'':
            self.mail_hash = hashlib.md5(str(self.id)+str(random.random())).hexdigest()
        super(NewsletterMail, self).save(**kwargs)
    
    def mark_sent(self):
        self.sent = True
        self.save()

    def get_message(self):

        newsletter = Newsletter.objects.filter(pk=newsletter_id)[0]
        return render_to_response(newsletter.template.path, {
            'newsletter' : newsletter,
            }, self.getcontent(), context_instance=RequestContext(request))
        
        if self.job.newsletter.reply_email!='':
            headers={'Reply-To': self.job.newsletter.reply_email}
        else:
            headers={}
        message = mail.EmailMessage(
            self.job.newsletter.subject,
            content,
            self.job.newsletter.from_email,
            [self.person.email],
            headers=headers,
        )
        message.content_subtype = "html"
        return message
    
    def get_content(self):
        pingback_url = "http://" + Site.objects.all()[0].domain + reverse('event.newsletter.ping', args=[self.mail_hash,'',])

        weblink = _("To view this email as a web page, click [here]")
        url = "http://" + Site.objects.all()[0].domain + reverse('event.newsletter.view', args=[self.mail_hash])
        weblink = weblink.replace("[",'<a href="'+url+'">').replace("]",'</a>')
        landing_page_url = "http://" + Site.objects.all()[0].domain + reverse('event.newsletter.landing', args=[self.mail_hash])
        
        return {
            'NEWSLETTER_URL': settings.NEWSLETTER_URL,
            'person': self.person,
            'group_object': self.job.group_object,
            'pingback_url': pingback_url,
            'weblink':weblink,
            'landing_page_url':landing_page_url,
        }
