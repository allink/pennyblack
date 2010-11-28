from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.utils import translation
from django.core import mail
from pennyblack import settings
from django.template import loader, Context, Template, RequestContext
from django.contrib.sites.models import Site
from django.db.models import signals
from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpRequest
from django.core.validators import email_re
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.core.mail.utils import DNS_NAME
from django.core.context_processors import csrf


from feincms.models import Base
from feincms.management.checker import check_database_schema
from feincms.utils import copy_model_instance
from feincms.module.medialibrary.models import MediaFile

# from Mailman.Bouncers.BouncerAPI import ScanMessages

from pennyblack.forms import CollectionSelectForm

import exceptions
import hashlib
import random
import sys
import datetime
# import spf
import socket
import poplib
import email

      
class Newsletter(Base):
    """A newsletter with subject and content
    can contain multiple jobs with mails to send"""
    name = models.CharField(verbose_name="Name", help_text="Wird nur intern verwendet.", max_length=100)
    active = models.BooleanField(default=True)
    sender = models.ForeignKey('Sender', verbose_name="Absender")
    subject = models.CharField(verbose_name="Betreff", max_length=250)
    reply_email = models.EmailField(verbose_name="Reply-to" ,blank=True)
    language = models.CharField(max_length=6, verbose_name="Sprache", choices=settings.LANGUAGES)
    header_image = models.ForeignKey(MediaFile, verbose_name="Header Image")
    header_url = models.URLField()
    site = models.ForeignKey(Site, verbose_name="Seite")
    
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
        for cls in self._feincms_content_types:
            for content in cls.objects.filter(parent=self):
                content.replace_links(job)
                content.save()
    
signals.post_syncdb.connect(check_database_schema(Newsletter, __name__), weak=False)

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
    def create_newsletter(self, collection):
        """
        Creates a newsletter for every NewsletterReceiverMixin
        """
        job = NewsletterJob(group_object=self, collection=collection)
        job.save()
        job.create_mails()
        return job
        
    def get_newsletter_receiver_collections(self):
        """
        Returns a dict of valid receiver collections
        has to be overriden in the object to return a tuple of querysets
        return (('all','clients'),)
        """
        raise exeptions.NotImplementedError("Override this method in your class!")
    
    def get_newsletter_receivers(self, collection):
        """
        Tries to get a queryset named after collection bevore giving up.
        """
        collection_to_attr = dict(self.get_newsletter_receiver_collections())
        queryset = getattr(self, collection_to_attr[collection], None) # todo: wieder aufschluesseln
        if queryset:
            return queryset
        raise exeptions.NotImplementedError("Didn't find any subset, maybe you didn't implement get_newsletter_receiver_collections.")

class NewsletterJobUnitAdmin(admin.ModelAdmin):
    change_form_template = "admin/pennyblack/jobunit/change_form.html"
    
    def create_newsletter(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        if len(obj.get_newsletter_receiver_collections()) == 1:
            job = obj.create_newsletter(obj.get_newsletter_receiver_collections()[0][0])
            return HttpResponseRedirect(reverse('admin:pennyblack_newsletterjob_change', args=(job.id,)))            
        if request.method == 'POST':
            form = CollectionSelectForm(data=request.POST, group_object=obj)
            if form.is_valid():
                job = obj.create_newsletter(form.cleaned_data['collection'])
                return HttpResponseRedirect(reverse('admin:pennyblack_newsletterjob_change', args=(job.id,)))
        else:
            form = CollectionSelectForm(group_object=obj)
        context = {
            'adminform':form,
            'form_url' : reverse('admin:pennyblack_newsletterjobunit_create_newsletter', args=(object_id,))
        }
        context.update(csrf(request))
        return render_to_response('admin/pennyblack/jobunit/select_receiver_collection.html',context)
            
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(NewsletterJobUnitAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^(?P<object_id>\d+)/create_newsletter/$', self.admin_site.admin_view(self.create_newsletter), name='pennyblack_newsletterjobunit_create_newsletter'),
        )
        return my_urls + urls
        


class NewsletterJob(models.Model):
    """A bunch of participants wich receive a newsletter"""
    newsletter = models.ForeignKey(Newsletter, related_name="jobs", null=True, limit_choices_to = {'active': True})
    status = models.IntegerField(choices=settings.JOB_STATUS, default=1)
    date_created = models.DateTimeField(verbose_name="Created", default=datetime.datetime.now())
    date_deliver_start = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Started", default=None)
    date_deliver_finished = models.DateTimeField(blank=True, null=True, verbose_name="Delivering Finished", default=None)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    group_object = generic.GenericForeignKey('content_type', 'object_id')
    collection = models.CharField(max_length=20)
    
    #ga tracking
    utm_campaign = models.SlugField(verbose_name="Utm Campaign")
    
    
    class Meta:
        ordering = ('date_created',)
        verbose_name = "Newsletter delivery task"
        verbose_name_plural = "Newsletter delivery tasks"
        
    def __unicode__(self):
        return (self.newsletter.subject if self.newsletter is not None else "unasigned NewsletterJob")
    
    def delete(self, *args, **kwargs):
        if self.newsletter.active == False:
            self.newsletter.delete()
        super(NewsletterJob, self).delete(*args, **kwargs)
    
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
    
    def create_mails(self):
        """
        Create mails for every NewsletterReceiverMixin in self.group_object.
        """
        if not hasattr(self.group_object, 'get_newsletter_receivers'):
            raise exceptions.NotImplementedError('Object needs to implement get_newsletter_receivers')
        for receiver in self.group_object.get_newsletter_receivers(self.collection).all():
            self.mails.add(Mail(person=receiver))
    
    def add_link(self, link):
        """
        Adds a link and returns a replacement link
        """
        link = Link(link_target=link, job=self)
        link.save()
        return self.newsletter.get_base_url() + reverse('pennyblack.redirect_link', kwargs={'mail_hash':'{{mail.mail_hash}}','link_hash':link.link_hash}).replace('%7B','{').replace('%7D','}')
    
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
        

class Link(models.Model):
    job = models.ForeignKey(NewsletterJob, related_name='links')
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

class Mail(models.Model):
    """
    This is a single Mail, it's part of a NewsletterJob
    """
    viewed = models.DateTimeField(default=None, null=True)
    bounced = models.BooleanField(default=False)
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
        super(Mail, self).save(**kwargs)
    
    def mark_sent(self):
        self.sent = True
        self.save()
    
    def mark_viewed(self):
        if not self.viewed:
            self.viewed = datetime.datetime.now()
            self.save()
    
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
        if self.job.newsletter.reply_email!='':
            headers={'Reply-To': self.job.newsletter.reply_email}
        else:
            headers={}
        message = mail.EmailMessage(
            self.job.newsletter.subject,
            self.get_content(),
            self.job.newsletter.sender.email,
            [self.person.email],
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
        }

class Sender(models.Model):
    email = models.EmailField(verbose_name="Von E-Mail Adresse")
    name = models.CharField(verbose_name="Von Name", help_text="Wird in vielen E-Mail Clients als Von angezeit.", max_length=100)
    pop_username = models.CharField(verbose_name="Pop3 Username", max_length=100, blank=True)
    pop_password = models.CharField(verbose_name="Pop3 Passwort", max_length=100, blank=True)
    pop_server = models.CharField(verbose_name="Pop3 Server", max_length=100, blank=True)
    pop_port = models.IntegerField(verbose_name="Pop3 Port", max_length=100, default=110)
    
    def __unicode__(self):
        return self.email
    
    def check_spf(self):
        """
        Check if sender is authorised by sender policy framework
        """
        # todo: wieder aufnehmen
        # return spf.check(i=socket.gethostbyname(DNS_NAME.get_fqdn()),s=self.email,h=DNS_NAME.get_fqdm())
    
    def spf_result(self):
        return self.check_spf()
    check_spf.short_description = "spf Result"
    
    def get_mail(self):
        conn = poplib.POP3(self.pop_server, self.pop_port)
        conn.user(self.pop_username)
        conn.pass_(self.pop_password)
        (numMessages, totalSize) = conn.stat()
        print 'messages '+str(numMessages)
        print 'size '+str(totalSize)
        for i in range(1,numMessages+1):
            (comment, lines, octets) = conn.retr(i)
            lines.append('')
            data = '\n'.join(lines)
            mime = email.message_from_string(data)
            # print ScanMessages(None, mime)
        conn.quit()
        
    