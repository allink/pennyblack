from django.contrib import admin
from django.core.mail.utils import DNS_NAME
from django.db import models
from django.utils.translation import ugettext_lazy as _

from pennyblack import settings

if settings.BOUNCE_DETECTION_ENABLE:
    from Mailman.Bouncers.BouncerAPI import ScanText

import imaplib
import datetime
import socket
try:
    import spf
    ENABLE_SPF = True
except IOError:
    # spf fails to load on a system which is offline because of missing resolv.conf
    ENABLE_SPF = False
except ImportError:
    # spf missing
    ENABLE_SPF = False
    

#-----------------------------------------------------------------------------
# Sender
#-----------------------------------------------------------------------------
class Sender(models.Model):
    """
    A sender for the from and reply to fields of the newsletter.
    """
    email = models.EmailField(verbose_name=_("from e-mail address"))
    name = models.CharField(verbose_name=_("from name"), help_text=_("many e-mail clients show this as from."), max_length=100)
    imap_username = models.CharField(verbose_name=_("imap username"), max_length=100, blank=True)
    imap_password = models.CharField(verbose_name=_("imap passwort"), max_length=100, blank=True)
    imap_server = models.CharField(verbose_name=_("imap server"), max_length=100, blank=True)
    imap_port = models.IntegerField(verbose_name=_("imap port"), max_length=100, default=143)
    imap_ssl = models.BooleanField(verbose_name=_("use ssl"), default=False)
    get_bounce_emails = models.BooleanField(verbose_name=_("get bounce e-mails"), default=False)
    
    class Meta:
        verbose_name = _('sender')
        verbose_name_plural = _('senders')
        app_label = 'pennyblack'
    
    def __unicode__(self):
        return self.email
    
    def check_spf(self):
        """
        Check if sender is authorised by sender policy framework
        """
        if not ENABLE_SPF:
            return False
        return spf.check(i=socket.gethostbyname(DNS_NAME.get_fqdn()),s=self.email,h=DNS_NAME.get_fqdn())
    
    def spf_result(self):
        return self.check_spf()
    check_spf.short_description = "spf Result"
    
    def get_mail(self):
        """
        Checks the inbox of this sender and prcesses the bounced emails
        """
        from pennyblack.models import Mail
        if not settings.BOUNCE_DETECTION_ENABLE:
            return
        oldest_date = datetime.datetime.now()-datetime.timedelta(days=settings.BOUNCE_DETECTION_DAYS_TO_LOOK_BACK)
        try:
            if self.imap_ssl:
                ssl_class = imaplib.IMAP4_SSL
            else:
                ssl_class = imaplib.IMAP4
            conn = ssl_class(self.imap_server, int(self.imap_port))
            conn.login(self.imap_username, self.imap_password)
            if conn.select(settings.BOUNCE_DETECTION_BOUNCE_EMAIL_FOLDER)[0] != 'OK':
                conn.create(settings.BOUNCE_DETECTION_BOUNCE_EMAIL_FOLDER)
            conn.select('INBOX')
            typ, data = conn.search(None, 'ALL')
            for num in data[0].split():
                typ, data = conn.fetch(num, '(RFC822)')
                if not data or not data[0]:
                    continue
                addrs = ScanText(data[0][1])
                addrs = addrs.split(';')
                if len(addrs) == 1 and len(addrs[0]) == 0:
                    continue
                for addr in addrs:
                    mailquery = Mail.objects.filter(email=addr).filter(job__date_deliver_finished__gte=oldest_date)
                    # ping all newsletter receivers
                    for mail in mailquery:
                        mail.bounce()
                if conn.copy(num,settings.BOUNCE_DETECTION_BOUNCE_EMAIL_FOLDER)[0] == 'OK':
                    conn.store(num, '+FLAGS', r'\Deleted')
            conn.expunge()
            conn.close()
            conn.logout()
        except imaplib.IMAP4.error, e:
            return
        
class SenderAdmin(admin.ModelAdmin):
    list_display = ('email', 'name',)
    fields = ('email', 'name', 'imap_username', 'imap_password', 'imap_server', 'imap_port', 'imap_ssl', 'get_bounce_emails', 'spf_result',)
    readonly_fields = ('spf_result',)

