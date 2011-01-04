from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.template import Context, Template, TemplateSyntaxError
from django.forms.util import ErrorList
from django.core import files

from pennyblack import settings

from feincms.content.richtext.models import RichTextContentAdminForm, RichTextContent
from feincms.module.medialibrary.models import MediaFile

import re
import os
import Image

HREF_RE = re.compile(r'href\="([^"><]+)"')

class NewsletterSectionAdminForm(RichTextContentAdminForm):
    def clean(self):
        cleaned_data = super(NewsletterSectionAdminForm, self).clean()
        try:
            t = Template(cleaned_data['text'])
        except TemplateSyntaxError, e:
            self._errors["text"] = ErrorList([e])
        try:
            t = Template(cleaned_data['title'])
        except TemplateSyntaxError, e:
            self._errors["title"] = ErrorList([e])
        return cleaned_data
    
    class Meta:
        exclude = ('image_thumb',)

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
            replacelink = job.add_link(match.group(1))
            self.text = ''.join((self.text[:match.start(1)+offset], replacelink, self.text[match.end(1)+offset:]))
            offset += len(replacelink) - len(match.group(1))
        
    def get_template(self):
        """
        Creates a template
        """
        return Template("""{%% extends "%s" %%}
        {%% block title %%}%s{%% endblock %%}
        {%% block text %%}%s{%% endblock %%}
        """ % (self.baselayout, self.title, self.text,))
    
    def render(self, request, **kwargs):
        context = request.content_context
        context.update({'content':self, 'content_width':settings.NEWSLETTER_CONTENT_WIDTH})
        if hasattr(self,'get_extra_context'):
            context.update(self.get_extra_context())
        return self.get_template().render(Context(context))


class TextWithImageNewsletterContent(TextOnlyNewsletterContent):
    """
    Like a TextOnlyNewsletterContent but with extra image field
    """
    image_original = models.ForeignKey(MediaFile)
    image_thumb = models.ImageField(upload_to='newsletter/images', blank=True)
    position = models.CharField(max_length=10, choices=settings.TEXT_AND_IMAGE_CONTENT_POSITIONS)
    
    baselayout = "content/text_and_image/section.html"
    
    class Meta:
        abstract = True
        verbose_name = _('text and image content')
        verbose_name_plural = _('text and image contents')
    
    def get_extra_context(self):
        image_width = settings.NEWSLETTER_CONTENT_WIDTH if self.position == 'center' else settings.TEXT_AND_IMAGE_CONTENT_IMAGE_WIDTH_SIDE
        text_width = settings.NEWSLETTER_CONTENT_WIDTH if self.position == 'center' else (settings.NEWSLETTER_CONTENT_WIDTH - 20 - settings.TEXT_AND_IMAGE_CONTENT_IMAGE_WIDTH_SIDE)
        return {
            'image_width': image_width,
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
            
    def save(self, *args, **kwargs):
        image_width = settings.NEWSLETTER_CONTENT_WIDTH if self.position == 'center' else settings.TEXT_AND_IMAGE_CONTENT_IMAGE_WIDTH_SIDE
        im=Image.open(self.image_original.file.path)
        im.thumbnail((image_width, 1000), Image.ANTIALIAS)
        img_temp = files.temp.NamedTemporaryFile(delete=True)
        im.save(img_temp,'jpeg')
        img_temp.flush()
        self.image_thumb.save(os.path.split(self.image_original.file.name)[1], files.File(img_temp), save=False)
        super(TextWithImageNewsletterContent, self).save(*args, **kwargs)
        
    
