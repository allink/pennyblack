from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.template import Context, Template, TemplateSyntaxError
from django.forms.util import ErrorList

from pennyblack import settings

from feincms.content.richtext.models import RichTextContentAdminForm, RichTextContent

import re

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
        return self.get_template().render(Context(request.content_context))


class TextWithImageNewsletterContent(TextOnlyNewsletterContent):
    """
    Like a TextOnlyNewsletterContent but with extra image field
    """
    image_original = models.ImageField(upload_to='newsletter/images')
    
    baselayout = "content/text_and_image/section.html"
    
    class Meta:
        abstract = True
        verbose_name = _('text and image content')
        verbose_name_plural = _('text and image contents')
    
    def get_template(self):
        """
        Creates a template
        """
        image_tag = """<img src="{{NEWSLETTER_URL}}default_image.jpg" width="100" height="116" />"""
        return Template("""{%% extends "%s" %%}
        {%% block title %%}%s{%% endblock %%}
        {%% block text %%}%s{%% endblock %%}
        {%% block image %%}%s{%% endblock %%}
        """ % (self.baselayout, self.title, self.text, image_tag))
