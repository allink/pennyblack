from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import translation

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

    content_type = models.ForeignKey('contenttypes.ContentType', null=True)
    object_id = models.PositiveIntegerField(null=True)
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
        if self.count_mails_total() == '0':
            return 0
        return round(float(self.count_mails_sent())/float(self.count_mails_total()) * 100)
    
    def count_mails_viewed(self):
        return self.mails.exclude(viewed=None).count()
    count_mails_viewed.short_description = '# of views'

    @property
    def percentage_mails_viewed(self):
        if self.count_mails_total() == '0':
            return 0
        return round(float(self.count_mails_viewed())/float(self.count_mails_total()) * 100)
    
    def count_mails_bounced(self):
        return self.mails.filter(bounced=True).count()
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
