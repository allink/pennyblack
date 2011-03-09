from django.db import models

from pennyblack.models import Newsletter
from pennyblack.options import NewsletterReceiverMixin, JobUnitMixin
from pennyblack.content.richtext import TextOnlyNewsletterContent, \
    TextWithImageNewsletterContent

Newsletter.register_templates({
    'key': 'base',
    'title': 'Generic Newsletter',
    'path': 'pennyblack/base_newsletter.html',
    'regions': (
        ('main', 'Main Region'),
        ),
    })
    
Newsletter.create_content_type(TextOnlyNewsletterContent)
Newsletter.create_content_type(TextWithImageNewsletterContent)
