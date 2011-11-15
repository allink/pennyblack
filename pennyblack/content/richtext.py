from django.core import files
from django.db import models
from django.forms.util import ErrorList
from django.template import Context, Template, TemplateSyntaxError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from pennyblack import settings
from pennyblack.models.link import check_if_redirect_url, is_link

from feincms.content.richtext.models import RichTextContentAdminForm, RichTextContent
from feincms.module.medialibrary.models import MediaFile

import re
import os
import Image
import exceptions

HREF_RE = re.compile(r'href\="((\{\{[^}]+\}\}|[^"><])+)"')

class NewsletterSectionAdminForm(RichTextContentAdminForm):
    def clean(self):
        cleaned_data = super(NewsletterSectionAdminForm, self).clean()
        try:
            t = Template(cleaned_data['text'])
        except TemplateSyntaxError, e:
            self._errors["text"] = ErrorList([e])
        except exceptions.KeyError:
            pass
        try:
            t = Template(cleaned_data['title'])
        except TemplateSyntaxError, e:
            self._errors["title"] = ErrorList([e])
        except exceptions.KeyError:
            pass
        return cleaned_data
    
    class Meta:
        exclude = ('image_thumb', 'image_width', 'image_height', 'image_url_replaced')
    
    def __init__(self, *args, **kwargs):
        super(NewsletterSectionAdminForm, self).__init__(*args, **kwargs)
        self.fields.insert(0, 'title', self.fields.pop('title'))

class TextOnlyNewsletterContent(RichTextContent):
    """
    Has a title and a text wich both can contain template code.
    """
    title = models.CharField(max_length=500)
    form = NewsletterSectionAdminForm
    feincms_item_editor_form = NewsletterSectionAdminForm

    feincms_item_editor_includes = {
        'head': [ settings.TINYMCE_CONFIG_URL ],
        }
    
    baselayout = "content/text_only/section.html"

    class Meta:
        abstract = True
        verbose_name = _('text only content')
        verbose_name_plural = _('text only contents')

    def replace_links(self, job):
        """
        Replaces all links and inserts pingback links
        """
        offset = 0
        for match in HREF_RE.finditer(self.text):
            link = match.group(1)
            if check_if_redirect_url(link):
                continue
            # don't replace links to proxy view
            if u'link_url' in link:
                continue
            replacelink = job.add_link(link)
            self.text = ''.join((self.text[:match.start(1)+offset], replacelink, self.text[match.end(1)+offset:]))
            offset += len(replacelink) - len(match.group(1))
        
    def prepare_to_send(self):
        """
        insert link_style into all a tags
        """
        self.text = re.sub(r"<a ","<a style=\"{% get_newsletterstyle request link_style %}\"", self.text)
        self.save()
        
    def get_template(self):
        """
        Creates a template
        """
        return Template("""{%% extends "%s" %%}
        {%% load pennyblack_tags %%}
        {%% block title %%}%s{%% endblock %%}
        {%% block text %%}%s{%% endblock %%}
        """ % (self.baselayout, self.title, self.text,))
    
    def render(self, request, **kwargs):
        context = request.content_context
        context['request'] = request
        context.update({'content':self, 'content_width':settings.NEWSLETTER_CONTENT_WIDTH})
        if hasattr(self,'get_extra_context'):
            context.update(self.get_extra_context())
        return self.get_template().render(Context(context))


class TextWithImageNewsletterContent(TextOnlyNewsletterContent):
    """
    Like a TextOnlyNewsletterContent but with extra image field
    """
    image_original = models.ForeignKey(MediaFile)
    image_thumb = models.ImageField(upload_to='newsletter/images', blank=True,
        width_field='image_width', height_field='image_height')
    image_width = models.IntegerField(default=0)
    image_height = models.IntegerField(default=0)
    image_url = models.CharField(max_length=250 ,blank=True)
    image_url_replaced = models.CharField(max_length=250, default='')
    position = models.CharField(max_length=10, choices=settings.TEXT_AND_IMAGE_CONTENT_POSITIONS)
    
    baselayout = "content/text_and_image/section.html"
    
    class Meta:
        abstract = True
        verbose_name = _('text and image content')
        verbose_name_plural = _('text and image contents')
    
    def get_extra_context(self):
        text_width = settings.NEWSLETTER_CONTENT_WIDTH if self.position == 'top' else (settings.NEWSLETTER_CONTENT_WIDTH - 20 - settings.TEXT_AND_IMAGE_CONTENT_IMAGE_WIDTH_SIDE)
        return {
            'image_width': self.image_width,
            'image_height': self.image_height,
            'text_width': text_width,
        }
    
    def get_template(self):
        """
        Creates a template
        """
        return Template("""{%% extends "%s" %%}
        {%% block title %%}%s{%% endblock %%}
        {%% block text %%}%s{%% endblock %%}
        """ % (self.baselayout, self.title, self.text))
    
    def get_image_url(self, context=None):
        """
        Gives the repalced url back, if no mail is present it gives instead
        the original url.
        """
        if context is None:
            return self.image_url
        template = Template(self.image_url_replaced)
        return template.render(context)
            
    def replace_links(self, job):
        super(TextWithImageNewsletterContent, self).replace_links(job)
        if not is_link(self.image_url, self.image_url_replaced):
            self.image_url_replaced = job.add_link(self.image_url)
            self.save()
            
    def save(self, *args, **kwargs):
        image_width = settings.NEWSLETTER_CONTENT_WIDTH if self.position == 'top' else settings.TEXT_AND_IMAGE_CONTENT_IMAGE_WIDTH_SIDE
        im=Image.open(self.image_original.file.path)
        im.thumbnail((image_width, 1000), Image.ANTIALIAS)
        img_temp = files.temp.NamedTemporaryFile()
        im.save(img_temp,'jpeg', quality=settings.JPEG_QUALITY, optimize=True)
        img_temp.flush()
        self.image_thumb.save(os.path.split(self.image_original.file.name)[1], files.File(img_temp), save=False)
        super(TextWithImageNewsletterContent, self).save(*args, **kwargs)
        
    
