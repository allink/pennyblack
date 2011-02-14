from django.core.urlresolvers import resolve
from django.db import models

import datetime
import hashlib
import random

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
    job = models.ForeignKey('pennyblack.Job', related_name='links')
    link_hash = models.CharField(max_length=32, blank=True)
    link_target = models.CharField(verbose_name="Adresse", max_length=500)
    
    class Meta:
        verbose_name = 'Link'
        verbose_name_plural = 'Links'
        app_label = 'pennyblack'

    def __unicode__(self):
        return self.link_target
    
    def click_count(self):
        """
        Returns the total click count.
        """
        return self.clicks.count()
    click_count.short_description = 'Click count'
    
    def click(self,mail):
        """
        Creates a LinkClick and returns the link target
        """
        click = LinkClick(link=self, mail=mail)
        click.save()
        return self.link_target

    def save(self, **kwargs):
        if self.link_hash == u'':
            self.link_hash = hashlib.md5(str(self.id)+str(random.random())).hexdigest()
        super(Link, self).save(**kwargs)
        
class LinkClick(models.Model):
    link = models.ForeignKey('pennyblack.Link', related_name='clicks')
    mail = models.ForeignKey('pennyblack.Mail', related_name='clicks')
    date = models.DateTimeField(default=datetime.datetime.now())
    
    class Meta:
        app_label = 'pennyblack'
        
