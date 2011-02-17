from django.contrib import admin
from django.core.mail.utils import DNS_NAME
from django.db import models

from pennyblack import settings

if settings.BOUNCE_DETECTION_ENABLE:
    from Mailman.Bouncers.BouncerAPI_new import ScanText

import imaplib
import datetime
import socket
import spf

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
    
    class Meta:
        verbose_name = 'Sender'
        verbose_name_plural = 'Senders'
        app_label = 'pennyblack'
    
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
            return
        
class SenderAdmin(admin.ModelAdmin):
    list_display = ('email', 'name',)
    fields = ('email', 'name', 'imap_username', 'imap_password', 'imap_server', 'imap_port', 'get_bounce_emails', 'spf_result',)
    readonly_fields = ('spf_result',)

