# coding=utf-8
from django.db.models import signals
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail.utils import DNS_NAME
from django.core.urlresolvers import reverse, resolve
from django.core.validators import email_re
from django.http import HttpResponseRedirect, HttpRequest
from django.template import loader, Context, Template, RequestContext
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from feincms.management.checker import check_database_schema
from feincms.models import Base
from feincms.module.medialibrary.models import MediaFile
from feincms.utils import copy_model_instance

from pennyblack import settings

if settings.BOUNCE_DETECTION_ENABLE:
    from Mailman.Bouncers.BouncerAPI_new import ScanText

import exceptions
import datetime
import hashlib
import imaplib
import random
import socket
import spf
import sys

#-----------------------------------------------------------------------------
# Newsletter
#-----------------------------------------------------------------------------
class NewsletterManager(models.Manager):
    def active(self):
        """
        Filters all active newsletters
        """
        return self.filter(active=True)
    
    def massmail(self):
        """
        Filters all newsletter avaiable for massmailing
        """
        return self.active().filter(newsletter_type__in=settings.NEWSLETTER_TYPE_MASSMAIL)
        
    def workflow(self):
        """
        Filters all newsletter avaiable in a workflow eg. signupmail
        """
        return self.active().filter(newsletter_type__in=settings.NEWSLETTER_TYPE_WORKFLOW)
    
    def get_workflow_newsletter_by_name(self, name):
        try:
            return self.workflow().get(name__iexact=name, language=translation.get_language())
        except ObjectDoesNotExist:
            pass
        try:
            return self.workflow().get(name__iexact=name, language=settings.LANGUAGE_CODE)
        except ObjectDoesNotExist:
            pass
        try:
            return self.workflow().filter(name__iexact=name)[0]
        except:
            return None

class Newsletter(Base):
    """A newsletter with subject and content
    can contain multiple jobs with mails to send"""
    name = models.CharField(verbose_name="Name", help_text="Wird nur intern verwendet.", max_length=100)
    active = models.BooleanField(default=True)
    newsletter_type = models.IntegerField(choices=settings.NEWSLETTER_TYPE, verbose_name="Art", help_text="Kann später nicht mehr geändert werden")
    sender = models.ForeignKey('Sender', verbose_name="Absender")
    subject = models.CharField(verbose_name="Betreff", max_length=250)
    reply_email = models.EmailField(verbose_name="Reply-to" ,blank=True)
    language = models.CharField(max_length=6, verbose_name="Sprache", choices=settings.LANGUAGES)
    header_image = models.ForeignKey(MediaFile, verbose_name="Header Image")
    header_url = models.URLField()
    site = models.ForeignKey(Site, verbose_name="Seite")
    
    objects = NewsletterManager()
    
    #ga tracking
    utm_source = models.SlugField(verbose_name="Utm Source", default="newsletter")
    utm_medium = models.SlugField(verbose_name="Utm Medium", default="cpc")

    class Meta:
        ordering = ('subject',)
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"
            
    def __unicode__(self):
        return self.name
    
    def is_valid(self):
        if self.subject == '':
            return False
        # todo: check if email is valid
        return True
    
    def create_snapshot(self):
        snapshot = copy_model_instance(self, exclude=('id',))
        snapshot.active = False
        snapshot.save()
        snapshot.copy_content_from(self)
        return snapshot
        
    def get_base_url(self):
        return "http://" + self.site.domain
        
    def replace_links(self, job):
        """
        Searches al links in content sections
        """
        if self.is_workflow():
            job = self.get_default_job()
        for cls in self._feincms_content_types:
            for content in cls.objects.filter(parent=self):
                content.replace_links(job)
                content.save()
        if not check_if_redirect_url(self.header_url):
            self.header_url = job.add_link(self.header_url)
            self.save()
        
    def get_default_job(self):
        try:
            return self.jobs.get(content_type=None)
        except ObjectDoesNotExist:
            return Job.objects.create(newsletter=self, status=32)            
    
    def is_workflow(self):
        return self.newsletter_type in settings.NEWSLETTER_TYPE_WORKFLOW 
    def send(self, person, group=None):
        """
        Sends this newsletter to "person" with optional "group".
        This works only with newsletters which are workflow newsletters.
        """
        if not self.is_workflow():
            raise exceptions.AttributeError('only newsletters with type workflow can be sent')
        # search newsletter job wich hash the same group or create it if it doesn't exist
        try:
            if group:
                ctype = ContentType.objects.get_for_model(group)
                job = self.jobs.get(content_type__pk=ctype.id, object_id=group.id)
            else:
                job = self.jobs.get(content_type=None)
        except ObjectDoesNotExist:
            if group:
                kw = {'group_object':group}
            else:
                kw = {}
            job=Job.objects.create(newsletter=self, status=32, #readonly
                **kw)
        self.replace_links(job)
        mail = job.create_mail(person)
        try:
            message = mail.get_message()
            message.send()
        except:
            raise
        else:
            mail.mark_sent()
            

    
signals.post_syncdb.connect(check_database_schema(Newsletter, __name__), weak=False)


#-----------------------------------------------------------------------------
# Job
#-----------------------------------------------------------------------------
class Job(models.Model):
    """A bunch of participants wich receive a newsletter"""
    newsletter = models.ForeignKey(Newsletter, related_name="jobs", null=True)
    status = models.IntegerField(choices=settings.JOB_STATUS, default=1)
    date_created = models.DateTimeField(verbose_name="Created", default=datetime.datetime.now())
    date_deliver_start = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Started", default=None)
    date_deliver_finished = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Finished", default=None)

    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    group_object = generic.GenericForeignKey('content_type', 'object_id')
    collection = models.TextField(blank=True)
    
    #ga tracking
    utm_campaign = models.SlugField(verbose_name="Utm Campaign")
    
    
    class Meta:
        ordering = ('date_created',)
        verbose_name = "Newsletter delivery task"
        verbose_name_plural = "Newsletter delivery tasks"
        
    def __unicode__(self):
        return (self.newsletter.subject if self.newsletter is not None else "unasigned Job")
    
    def delete(self, *args, **kwargs):
        if self.newsletter.active == False:
            self.newsletter.delete()
        super(Job, self).delete(*args, **kwargs)
    
    def count_mails_total(self):
        return str(self.mails.count())
    count_mails_total.short_description = '# of mails'
    
    def count_mails_sent(self):
        return str(self.mails.filter(sent=True).count())
    count_mails_sent.short_description = '# of mails sent'

    @property
    def percentage_mails_sent(self):
        if self.count_mails_total() == '0':
            return 0
        return round(float(self.count_mails_sent())/float(self.count_mails_total()) * 100)
    
    def count_mails_viewed(self):
        return str(self.mails.exclude(viewed=None).count())
    count_mails_viewed.short_description = '# of views'

    @property
    def percentage_mails_viewed(self):
        if self.count_mails_total() == '0':
            return 0
        return round(float(self.count_mails_viewed())/float(self.count_mails_total()) * 100)
    
    def count_mails_bounced(self):
        return str(self.mails.filter(bounced=True).count())
    count_mails_bounced.short_description = '# of bounces'

    @property
    def percentage_mails_bounced(self):
        if self.count_mails_total() == '0':
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
        return Mail.objects.create(person=receiver, job=self)
        
    
    def add_link(self, link):
        """
        Adds a link and returns a replacement link
        """
        link = Link(link_target=link, job=self)
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

#-----------------------------------------------------------------------------
# Link
#-----------------------------------------------------------------------------
def check_if_redirect_url(url):
    """
    Checks if the url is a redirect url
    """
    if '{{base_url}}' == url[:len('{{base_url}}')]:
        try:
            result = resolve(url[len('{{base_url}}'):])
            if result[0].func_name == 'redirect_link':
                return True
        except:
            pass
    return False

class Link(models.Model):
    job = models.ForeignKey(Job, related_name='links')
    link_hash = models.CharField(max_length=32, blank=True)
    link_target = models.CharField(verbose_name="Adresse", max_length=500)
    
    def click_count(self):
        return self.clicks.count()
    click_count.short_description = 'Click count'
    
    def click(self,mail):
        """
        Creates a LinkClick and returns the link target
        """
        click = LinkClick(link=self, mail=mail)
        click.save()
        return self.link_target

    def __unicode__(self):
        return self.link_target

    def save(self, **kwargs):
        if self.link_hash == u'':
            self.link_hash = hashlib.md5(str(self.id)+str(random.random())).hexdigest()
        super(Link, self).save(**kwargs)
        
class LinkClick(models.Model):
    link = models.ForeignKey(Link, related_name='clicks')
    mail = models.ForeignKey('Mail', related_name='clicks')
    date = models.DateTimeField(default=datetime.datetime.now())

#-----------------------------------------------------------------------------
# Mail
#-----------------------------------------------------------------------------
class Mail(models.Model):
    """
    This is a single Mail, it's part of a Job
    """
    viewed = models.DateTimeField(default=None, null=True)
    bounced = models.BooleanField(default=False)
    sent = models.BooleanField(default=False)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    person = generic.GenericForeignKey('content_type', 'object_id')
    job = models.ForeignKey(Job, related_name="mails")
    mail_hash = models.CharField(max_length=32, blank=True)
    email = models.EmailField() # the address is stored when the mail is sent
    
    def __unicode__(self):
        return '%s to %s' % (self.job, self.person,)
        
    def save(self, **kwargs):
        if self.mail_hash == u'':
            self.mail_hash = hashlib.md5(str(self.id)+str(random.random())).hexdigest()
        super(Mail, self).save(**kwargs)
    
    def mark_sent(self):
        self.sent = True
        self.save()
    
    def mark_viewed(self):
        if not self.viewed:
            self.viewed = datetime.datetime.now()
            self.save()
    
    def on_landing(self, request):
        self.mark_viewed()
        if hasattr(self.person, 'on_landing') and hasattr(self.person.on_landing, '__call__'):
            self.person.on_landing(request)
        if self.job.content_type is not None and \
            hasattr(self.job.group_object, 'on_landing') and \
            hasattr(self.job.group_object.on_landing, '__call__'):
            self.group_object.on_landing(request)
    
    def is_valid(self):
        """
        Checks if this Mail is valid
        """
        return email_re.match(self.person.get_email())

    def get_email(self):
        return self.person.get_email()
    get_email.short_description = "E-Mail"

    def get_message(self):
        """
        Returns a email message object
        """
        self.email = self.person.get_email()
        if self.job.newsletter.reply_email!='':
            headers={'Reply-To': self.job.newsletter.reply_email}
        else:
            headers={}
        message = mail.EmailMessage(
            self.job.newsletter.subject,
            self.get_content(),
            self.job.newsletter.sender.email,
            [self.email],
            headers=headers,
        )
        message.content_subtype = "html"
        return message
    
    def get_content(self, webview=False):
        """
        Returns the mail html content
        """
        newsletter = self.job.newsletter
        context = self.get_context()
        context['newsletter'] = newsletter
        context['webview'] = webview
        request = HttpRequest()
        request.content_context = context
        return render_to_string(newsletter.template.path,
            context, context_instance=RequestContext(request))
        
    
    def get_context(self):
        """
        Returns the context of this email as a dict
        """        
        return {
            'person': self.person,
            'group_object': self.job.group_object,
            'mail':self,
            'base_url': self.job.newsletter.get_base_url()
        }
    
    def get_header_url(self):
        """
        Gets the header url for this email
        """
        return self.job.newsletter.header_url.replace('{{mail.mail_hash}}',self.mail_hash)

#-----------------------------------------------------------------------------
# Sender
#-----------------------------------------------------------------------------
class Sender(models.Model):
    email = models.EmailField(verbose_name="Von E-Mail Adresse")
    name = models.CharField(verbose_name="Von Name", help_text="Wird in vielen E-Mail Clients als Von angezeit.", max_length=100)
    imap_username = models.CharField(verbose_name="IMAP Username", max_length=100, blank=True)
    imap_password = models.CharField(verbose_name="IMAP Passwort", max_length=100, blank=True)
    imap_server = models.CharField(verbose_name="IMAP Server", max_length=100, blank=True)
    imap_port = models.IntegerField(verbose_name="IMAP Port", max_length=100, default=143)
    get_bounce_emails = models.BooleanField(verbose_name="Get bounce emails", default=False)
    
    def __unicode__(self):
        return self.email
    
    def check_spf(self):
        """
        Check if sender is authorised by sender policy framework
        """
        return spf.check(i=socket.gethostbyname(DNS_NAME.get_fqdn()),s=self.email,h=DNS_NAME.get_fqdm())
    
    def spf_result(self):
        return self.check_spf()
    check_spf.short_description = "spf Result"
    
    def get_mail(self):
        """
        Checks the inbox of this sender and prcesses the bounced emails
        """
        if not settings.BOUNCE_DETECTION_ENABLE:
            return
        oldest_date = datetime.datetime.now()-datetime.timedelta(days=settings.BOUNCE_DETECTION_DAYS_TO_LOOK_BACK)
        try:
            conn = imaplib.IMAP4(self.imap_server, self.imap_port)
            conn.login(self.imap_username, self.imap_password)
            if conn.select(settings.BOUNCE_DETECTION_BOUNCE_EMAIL_FOLDER)[0] != 'OK':
                conn.create(settings.BOUNCE_DETECTION_BOUNCE_EMAIL_FOLDER)
            conn.select()
            typ, data = conn.search(None, 'ALL')
            for num in data[0].split():
                typ, data = conn.fetch(num, '(RFC822)')
                addrs = ScanText(data[0][1])
                addrs = addrs.split(';')
                if len(addrs) == 1 and len(addrs[0]) == 0:
                    continue
                for addr in addrs:
                    mailquery = Mail.objects.filter(email=addr).filter(job__date_deliver_finished__gte=oldest_date)
                    mailquery.update(bounced=True)
                    # ping all newsletter receivers
                    for mail in mailquery:
                        mail.person.bounce_ping()
                if conn.copy(num,settings.BOUNCE_DETECTION_BOUNCE_EMAIL_FOLDER)[0] == 'OK':
                    conn.store(num, '+FLAGS', '\\Deleted')
            conn.expunge()
            conn.close()
            conn.logout()
        except imaplib.IMAP4.error, e:
            print e
            return
        
    