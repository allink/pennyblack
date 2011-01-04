from django.db import models

from pennyblack.models import Newsletter
from pennyblack.options import NewsletterReceiverMixin, JobUnitMixin
from pennyblack.content.richtext import TextOnlyNewsletterContent, \
    TextWithImageNewsletterContent

Newsletter.register_templates({
    'key': 'base',
    'title': 'Generic Newsletter',
    'path': 'base_newsletter.html',
    'regions': (
        ('main', 'Main Region'),
        ),
    })
    
Newsletter.create_content_type(TextOnlyNewsletterContent)
Newsletter.create_content_type(TextWithImageNewsletterContent)

class Group(models.Model, JobUnitMixin):
    name = models.CharField(max_length=20)
    class Meta:
        abstract = False
        
    def __unicode__(self):
        return self.name
        
    def get_newsletter_receiver_collections(self):
        return (('all',{}),)
    
    def get_receiver_queryset(self):
        return self.client_set.all()

class Client(models.Model, NewsletterReceiverMixin):
    fullname = models.CharField(max_length=20)
    email = models.CharField(max_length=100)
    groups = models.ManyToManyField(Group)