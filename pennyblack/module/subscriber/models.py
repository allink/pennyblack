from django.contrib import admin
from django.db import models

from pennyblack.options import NewsletterReceiverMixin, JobUnitMixin, JobUnitAdmin

import datetime

class NewsletterSubscriberManager(models.Manager):
    """
    Custom manager for NewsletterSubscriber to provide extra functionality
    """
    def get_or_add(self,email, **kwargs):
        """
        Gets a subscriber, if he doesn't exist it creates him.
        """
        try:
            return self.get(email__iexact=email)
        except self.model.DoesNotExist:
            return self.create(email=email.lower(), **kwargs)

class NewsletterSubscriber(models.Model, NewsletterReceiverMixin):
    """
    A generic newsletter subscriber
    """
    email = models.EmailField(verbose_name="Email address")
    groups = models.ManyToManyField('subscriber.SubscriberGroup',
        verbose_name="Groups", related_name='subscribers')
    date_subscribed = models.DateTimeField(verbose_name="Subscribe Date",
        default=datetime.datetime.now())
    
    objects = NewsletterSubscriberManager()
    
    class Meta:
        verbose_name = "Subscriber"
        verbose_name_plural = "Subscribers"
    
    def __unicode__(self):
        return self.email
    
    @classmethod
    def register_extension(cls, register_fn):
        """
        Call the register function of an extension. You must override this
        if you provide a custom ModelAdmin class and want your extensions to
        be able to patch stuff in.
        """
        register_fn(cls, NewsletterSubscriberAdmin)


class NewsletterSubscriberAdmin(admin.ModelAdmin):
    search_fields = ('email',)
    list_filter = ('groups',)
    filter_horizontal = ('groups',)
    

class SubscriberGroupManager(models.Manager):
    """
    Custom manager for SubscriberGroup to provide extra functionality
    """
    def get_or_add(self, name, **kwargs):
        """
        Gets a group, if she doesn't exist it creates her.
        """
        try:
            return self.get(name__iexact=name)
        except self.model.DoesNotExist:
            return self.create(name=name, **kwargs)
    
class SubscriberGroup(models.Model, JobUnitMixin):
    """
    Groups to add newsletter subscribers
    """
    name = models.CharField(max_length=50, verbose_name="Name", unique=True)
    
    objects = SubscriberGroupManager()

    class Meta:
        verbose_name = "SubscriberGroup"
        verbose_name_plural = "SubscriberGroups"
    
    def __unicode__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.subscribers.count()
    
    def get_member_count(self):
        return self.member_count
    get_member_count.short_description = "Member Count"
    
    def get_newsletter_receiver_collections(self):
        """
        Every Group has only one collection
        """
        return (('all',{}),)
    
    def get_receiver_queryset(self):
        """
        Return all group members
        """
        return self.subscribers.all()
    
class SubscriberGroupAdmin(JobUnitAdmin):
    list_display = ('__unicode__', 'get_member_count')
    