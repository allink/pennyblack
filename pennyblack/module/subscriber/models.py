from django.db import models

from pennyblack.options import NewsletterReceiverMixin

class NewsletterSubscriber(models.Model, NewsletterReceiverMixin):
    """
    A generic newsletter subscriber
    """
    email = models.EmailField()