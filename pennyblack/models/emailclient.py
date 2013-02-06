"""
http://user-agent-string.info/
"""
from django.db import models
from django.utils.translation import ugettext_lazy as _

try:
    from django.utils import timezone
except ImportError:
    now = datetime.datetime.now
else:
    now = timezone.now


class EmailClient(models.Model):
    """
    Stores some information about the used email client and about the user
    """
    mail = models.ForeignKey('pennyblack.Mail', related_name='clients')
    user_agent = models.CharField(max_length=255, db_index=True)
    referer = models.CharField(max_length=1023, blank=True)
    ip_address = models.IPAddressField()
    visited = models.DateTimeField(default=now)

    class Meta:
        verbose_name = _('email client')
        verbose_name_plural = _('email clients')
        app_label = 'pennyblack'

    def __unicode__(self):
        return self.user_agent
