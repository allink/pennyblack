import hashlib
import random
from rfc822 import dump_address_pair

from django.contrib import admin
from django.contrib.contenttypes import generic
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch, reverse
from django.core.validators import validate_email
from django.db import models
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.template import RequestContext

from pennyblack import settings

try:
    from django.utils.timezone import now
except ImportError:
    from datetime import datetime
    now = datetime.now

from datetime import timedelta


#-----------------------------------------------------------------------------
# Mail
#-----------------------------------------------------------------------------
class MailManager(models.Manager):
    use_for_related_fields = True

    def most_clicked_first(self):
        return self.annotate(click_count=models.Count('clicks')).order_by('-click_count')


class Mail(models.Model):
    """
    This is a single Mail, it's part of a Job
    """
    viewed = models.DateTimeField(default=None, null=True)
    bounced = models.BooleanField(default=False)
    sent = models.BooleanField(default=False)
    content_type = models.ForeignKey('contenttypes.ContentType')
    object_id = models.PositiveIntegerField()
    person = generic.GenericForeignKey('content_type', 'object_id')
    job = models.ForeignKey('pennyblack.Job', related_name="mails")
    mail_hash = models.CharField(max_length=32, blank=True)
    email = models.EmailField()  # the address is stored when the mail is sent

    objects = MailManager()

    class Meta:
        verbose_name = 'mail'
        verbose_name_plural = 'mails'
        app_label = 'pennyblack'

    def __init__(self, *args, **kwargs):
        super(Mail, self).__init__(*args, **kwargs)
        self.extra_context = None
        self.extra_attachments = []

    def __unicode__(self):
        return u'%s to %s' % (self.job, self.person,)

    def save(self, **kwargs):
        if self.mail_hash == u'':
            self.mail_hash = hashlib.md5(str(self.id) + str(random.random())).hexdigest()
        super(Mail, self).save(**kwargs)

    def mark_sent(self):
        """
        Marks the email as beeing sent.
        """
        self.sent = True
        self.save()

    def mark_viewed(self, request=None, contact_type='link'):
        """
        Marks the email as beeing viewed and if it's not already viewed it
        stores the view date.
        """
        if request:
            params = {
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': request.META.get('REMOTE_ADDR', ''),
                'referer': request.META.get('HTTP_REFERER', ''),
                'contact_type': contact_type,
            }
            t = now() - timedelta(hours=1)
            if not self.clients.filter(**params).filter(visited__gt=t):
                self.clients.create(**params)
        if not self.viewed:
            self.viewed = now()
            self.save()

    def on_landing(self, request):
        """
        Is executed every time a user landed on the website after clicking on
        a link in this email. It tries to execute the on_landing method on the
        person object and on the group object.
        """
        self.mark_viewed(request, contact_type='link')
        if hasattr(self.person, 'on_landing') and hasattr(self.person.on_landing, '__call__'):
            self.person.on_landing(request)
        if self.job.content_type is not None and \
                hasattr(self.job.group_object, 'on_landing') and \
                hasattr(self.job.group_object.on_landing, '__call__'):
            self.group_object.on_landing(request)

    def bounce(self):
        """
        Is executed if this email is bounced.
        """
        self.bounced = True
        self.save()
        self.person.on_bounce(self)

    def unsubscribe(self):
        """
        Is executed if the unsubscribe link is clicked.
        """
        return self.person.unsubscribe()

    def is_valid(self):
        """
        Checks if this Mail is valid by validating the email address.
        """
        try:
            validate_email(self.person.get_email())
        except ValidationError:
            return False
        return True

    def get_email(self):
        """
        Gets the email address. If it has no email address set, it tries to
        get it from the person object.
        """
        if self.email != '':
            return self.email
        return self.person.get_email()
    get_email.short_description = "E-Mail"

    def get_message(self):
        """
        Returns a email message object
        """
        self.email = self.person.get_email()
        job = self.job
        headers = {}
        if job.newsletter.reply_email != '':
            headers.update({'Reply-To': job.newsletter.reply_email})
        if job.newsletter.newsletter_type == settings.NEWSLETTER_TYPE_MASSMAIL:
            headers.update({'Precedence': 'bulk'})
        try:
            headers.update({'List-Unsubscribe': "<%s>" % self.person.get_unsubscribe_url(mail=self, job=job, newsletter=job.newsletter)})
        except NotImplementedError:
            pass
        message = mail.EmailMessage(
            job.newsletter.subject,
            self.get_content(),
            dump_address_pair((job.newsletter.sender.name, job.newsletter.sender.email)),
            [self.email],
            headers=headers,
        )
        for attachment in job.newsletter.attachments.all():
            message.attachments.append((attachment.name, attachment.file.read(), attachment.mimetype))
        for attachment in self.extra_attachments:
            message.attachments.append(attachment)
        message.content_subtype = "html"
        return message

    def get_content(self, webview=False):
        """
        Renders the email content. If webview is True it includes also a
        html header and doesn't display the webview link.
        """
        newsletter = self.job.newsletter
        context = self.get_context()
        context['newsletter'] = newsletter
        context['webview'] = webview
        if isinstance(self.extra_context, dict):
            context.update(self.extra_context)
        request = HttpRequest()
        request.content_context = context
        return render_to_string(newsletter.template.path, context,
                                context_instance=RequestContext(request))

    def get_context(self):
        """
        Returns the context of this email as a dict.
        """
        return {
            'person': self.person,
            'group_object': self.job.group_object,
            'mail': self,
            'base_url': self.job.newsletter.get_base_url()
        }

    def get_header_url(self):
        """
        Gets the header url for this email.
        """
        return self.job.newsletter.header_url_replaced.replace('{{mail.mail_hash}}', self.mail_hash).replace('{{base_url}}', self.job.newsletter.get_base_url())

    @property
    def admin_change_url(self):
        if hasattr(self, '_admin_change_url'):
            return self._admin_change_url
        try:
            self._admin_change_url = reverse('admin:%s_%s_change' % (self.content_type.app_label, self.content_type.model), args=[self.object_id])
        except NoReverseMatch:
            return None
        return self._admin_change_url


class MailInline(admin.TabularInline):
    model = Mail
    max_num = 0
    can_delete = False
    fields = ('get_email',)
    readonly_fields = ('get_email',)

    def queryset(self, request):
        """
        Don't display Inlines if there are more than a certain amount
        """
        if request._pennyblack_job_obj.mails.count() > settings.JOB_MAIL_INLINE_COUNT:
            return super(MailInline, self).queryset(request).filter(pk=0)
        return super(MailInline, self).queryset(request)
