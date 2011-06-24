# coding=utf-8
import exceptions

from django.conf.urls.defaults import patterns, url
from django.core.exceptions import ImproperlyConfigured
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import signals
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from feincms.admin import editor
from feincms.admin import item_editor
from feincms.management.checker import check_database_schema
from feincms.models import Base
from feincms.utils import copy_model_instance

from pennyblack import settings

#-----------------------------------------------------------------------------
# Newsletter
#-----------------------------------------------------------------------------
class NewsletterManager(models.Manager):
    def active(self):
        """
        Filters all active newsletters
        """
        return self.filter(active=True)
    
    def massmail(self):
        """
        Filters all newsletter avaiable for massmailing
        """
        return self.active().filter(newsletter_type__in=settings.NEWSLETTER_TYPE_MASSMAIL)
        
    def workflow(self):
        """
        Filters all newsletter avaiable in a workflow eg. signupmail
        """
        return self.active().filter(newsletter_type__in=settings.NEWSLETTER_TYPE_WORKFLOW)
    
    def get_workflow_newsletter_by_name(self, name):
        """
        Tries to get a newsletter with the given name. First it tries to find
        one where the language matches the active language, later it tries to
        find one with the default language and if it doesn't find one it tries
        to get any newsletter with the given name before giving up.
        """
        try:
            return self.workflow().get(name__iexact=name, language=translation.get_language())
        except models.ObjectDoesNotExist:
            pass
        try:
            return self.workflow().get(name__iexact=name, language=settings.LANGUAGE_CODE)
        except models.ObjectDoesNotExist:
            pass
        try:
            return self.workflow().filter(name__iexact=name)[0]
        except:
            return None

class Newsletter(Base):
    """
    A newsletter with subject and content
    can contain multiple jobs with mails to send
    """
    name = models.CharField(verbose_name=_("name"), help_text=_("Is only to describe the newsletter."), max_length=100)
    active = models.BooleanField(default=True)
    newsletter_type = models.IntegerField(choices=settings.NEWSLETTER_TYPE,
        verbose_name=_("Type"), help_text=_("Can only be changed during creation."))
    sender = models.ForeignKey('pennyblack.Sender', verbose_name=_("sender"))
    subject = models.CharField(verbose_name=_("subject"), max_length=250)
    reply_email = models.EmailField(verbose_name=_("reply-to") ,blank=True)
    language = models.CharField(max_length=6, verbose_name=_("language"), choices=settings.LANGUAGES)
    header_image = models.ForeignKey('medialibrary.MediaFile', verbose_name=_("header image"))
    header_url = models.URLField()
    header_url_replaced = models.CharField(max_length=250, default='')
    site = models.ForeignKey('sites.Site', verbose_name=_("site"))    
    #ga tracking
    utm_source = models.SlugField(verbose_name=_("utm Source"), default="newsletter")
    utm_medium = models.SlugField(verbose_name=_("utm Medium"), default="cpc")
    
    objects = NewsletterManager()

    class Meta:
        ordering = ('subject',)
        verbose_name = _("Newsletter")
        verbose_name_plural = _("Newsletters")
        app_label = 'pennyblack'
            
    def __unicode__(self):
        return u'%s %s' % (self.name, self.language)
    
    def is_valid(self):
        """
        Checks if the newsletter is valid. A newsletter needs to have a
        subject to be valid.
        """
        if self.subject == '':
            return False
        # todo: check if email is valid
        return True
    
    def create_snapshot(self):
        """
        Makes a copy of itselve with all the content and returns the copy.
        """
        snapshot = copy_model_instance(self, exclude=('id',))
        snapshot.active = False
        snapshot.save()
        snapshot.copy_content_from(self)
        return snapshot
        
    def get_base_url(self):
        return "http://" + self.site.domain
        
    def replace_links(self, job):
        """
        Searches al links in content sections and replaces them with a link to
        the link tracking view.
        It also generates the header_url_replaced which is the same but for
        the header url.
        """
        from pennyblack.models.link import is_link
        if self.is_workflow():
            default_job = self.get_default_job()
        else:
            default_job = job
        for cls in self._feincms_content_types:
            for content in cls.objects.filter(parent=self):
                content.replace_links(default_job)
                content.save()
        if not is_link(self.header_url, self.header_url_replaced):
            self.header_url_replaced = default_job.add_link(self.header_url)
            self.save()
        if job.group_object and hasattr(job.group_object,'get_extra_links'):
            from exceptions import DeprecationWarning
            raise DeprecationWarning("get_extra_links is deprecated and will no longer work")
        
    def prepare_to_send(self):
        """
        Last hook before the newsletter is sent
        """
        for cls in self._feincms_content_types:
            for content in cls.objects.filter(parent=self):
                if hasattr(content, 'prepare_to_send'):
                    content.prepare_to_send()
    
    def get_default_job(self):
        """
        Tries to get the default job. If no default job exists it creates one.
        This is only used in workflow newsletters.
        """
        try:
            return self.jobs.get(content_type=None)
        except models.ObjectDoesNotExist:
            return self.jobs.create(status=32)            
    
    def is_workflow(self):
        """
        Returns True if it's type is a workflow newsletter.
        """
        return self.newsletter_type in settings.NEWSLETTER_TYPE_WORKFLOW 

    def send(self, person, group=None):
        """
        Sends this newsletter to "person" with optional "group".
        This works only with newsletters which are workflow newsletters.
        """
        if not self.is_workflow():
            raise exceptions.AttributeError('only newsletters with type workflow can be sent')
        # search newsletter job wich hash the same group or create it if it doesn't exist
        try:
            if group:
                ctype = ContentType.objects.get_for_model(group)
                job = self.jobs.get(content_type__pk=ctype.id, object_id=group.id)
            else:
                job = self.jobs.get(content_type=None)
        except models.ObjectDoesNotExist:
            if group:
                kw = {'group_object':group}
            else:
                kw = {}
            job=self.jobs.create(status=32, **kw) # 32=readonly
        self.replace_links(job)
        self.prepare_to_send()
        mail = job.create_mail(person)
        try:
            message = mail.get_message()
            message.send()
        except:
            raise
        else:
            mail.mark_sent()
    
    _view_links = {}
    
    @classmethod
    def register_view_link(cls, identifier, view):
        """
        Register a new view link
        Newsletter.register_view_link('my_identifier',view_function)
        """
        if identifier in cls._view_links.keys():
            return
        cls._view_links[identifier] = view
    
    @classmethod
    def add_view_link_to_job(cls, identifier,job):
        if identifier not in cls._view_links.keys():
            raise ImproperlyConfigured("no view with identifier '%s' found" % identifier)
        return job.add_link(cls._view_links[identifier], identifier=identifier)
        
        
            
Newsletter.__module__ = 'pennyblack.models'    
signals.post_syncdb.connect(check_database_schema(Newsletter, __name__), weak=False)

class NewsletterAdmin(editor.ItemEditor, admin.ModelAdmin):
    list_display = ('name', 'subject', 'language', 'newsletter_type')
    raw_id_fields = ('header_image',)
    fieldsets = (
        (None, {
            'fields': ['name', 'subject', 'sender', 'reply_email', 'template_key'],
        }),
        (_('Other options'), {
            'classes': ['collapse',],
            'fields': ('newsletter_type', 'language', 'utm_source','utm_medium', 'header_image', 'header_url', 'site'),
        }),
        item_editor.FEINCMS_CONTENT_FIELDSET,
    )
    exclude = ('header_url_replaced',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('newsletter_type',)
        return self.readonly_fields

    def queryset(self, request):
        return self.model.objects.active()

    def get_urls(self):
        urls = super(NewsletterAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^(?P<newsletter_id>\d+)/preview/$', 'pennyblack.views.preview')
        )
        return my_urls + urls
