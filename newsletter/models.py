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

from feincms.models import Base
from feincms.management.checker import check_database_schema
from feincms.admin import editor

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
    content = models.TextField()
    
    #ga tracking
    utm_source = models.SlugField(verbose_name="Utm Source", default="newsletter")
    utm_medium = models.SlugField(verbose_name="Utm Medium", default="cpc")

    class Meta:
        ordering = ('subject',)
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"
            
    def __unicode__(self):
        return self.name
    
    # def get_template(self):
    #     return Template('{%% extends "newsletter/email.html" %%}{%% block newscontainer %%}%s{%% endblock %%}' % (self.content,))

signals.post_syncdb.connect(check_database_schema(Newsletter, __name__), weak=False)

class NewsletterAdmin(editor.ItemEditor, admin.ModelAdmin):
    list_display = ('subject', 'from_email',)
    raw_id_fields = []
    #inlines = (NewsletterLinkInline,)


class NewsletterLink(models.Model):
    newsletter = models.ForeignKey(Newsletter)
    link_hash = models.CharField(max_length=32, blank=True)
    link_target = models.CharField(verbose_name="Adresse", max_length=500)
    click_count = models.IntegerField(default=0)
    
    def __unicode__(self):
        return self.link_target
    
    def save(self, **kwargs):
        if self.link_hash == u'':
            self.link_hash = hashlib.md5(str(self.id)+str(random.random())).hexdigest()
        super(NewsletterLink, self).save(**kwargs)

class NewsletterReceiver(object):
    """
    Abstract baseclass for every object that can receive a newsletter
    """
    class Meta:
        abstract = True
    
    def get_email(self):
        if hasattr(self,'email'):
            return self.email
        raise exceptions.NotImplementedError('Need a get_email implementation.')
            

class NewsletterJob(models.Model):
    """A bunch of participants wich receive a newsletter"""
    newsletter = models.ForeignKey(Newsletter, related_name="jobs", null=True)
    status = models.IntegerField(choices=((1,'Draft'),(2,'Pending'),(3,'Sending'),(4,'Finished'),(5,'Error'),), default=1)
    date_deliver_start = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Started", default=None)
    date_deliver_finished = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Finished", default=None)
    
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
            
    
    def create_mails(self):
        if not self.event == None:
            for participant in self.event.participants.all():
                self.mails.add(NewsletterMail(person=participant))
        if not self.group == None:
            for customer in self.group.customers.all():
                self.mails.add(NewsletterMail(person=customer))
    
    def send(self):
        if self.status != 1 and self.status != 5:
            return
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

    def get_message(self, template, event, group):
        pingback_url = "http://" + Site.objects.all()[0].domain + reverse('event.newsletter.ping', args=[self.mail_hash,'',])

        weblink = _("To view this email as a web page, click [here]")
        url = "http://" + Site.objects.all()[0].domain + reverse('event.newsletter.view', args=[self.mail_hash])
        weblink = weblink.replace("[",'<a href="'+url+'">').replace("]",'</a>')
        landing_page_url = "http://" + Site.objects.all()[0].domain + reverse('event.newsletter.landing', args=[self.mail_hash])

        content = template.render(Context({
            'NEWSLETTER_URL': settings.NEWSLETTER_URL,
            'person': self.person,
            'event': event,
            'group': group,
            'pingback_url': pingback_url,
            'weblink':weblink,
            'landing_page_url':landing_page_url,
        }))
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
        template = self.job.newsletter.get_template()
        return template.render(Context({
            'NEWSLETTER_URL': settings.NEWSLETTER_URL,
            'person': self.person,
            'event': self.job.event,
            'group': self.job.group,
        }))
