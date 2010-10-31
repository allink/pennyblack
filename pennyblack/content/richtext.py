from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.template import Context, Template, TemplateSyntaxError
from django.forms.util import ErrorList

from pennyblack import settings

from feincms.content.richtext.models import RichTextContentAdminForm, RichTextContent

import re

class NewsletterSectionAdminForm(RichTextContentAdminForm):
    def clean(self):
        cleaned_data = super(NewsletterSectionAdminForm, self).clean()
        try:
            t = Template(cleaned_data['text'])
        except TemplateSyntaxError, e:
            self._errors["text"] = ErrorList([e])
        return cleaned_data

class TextOnlyNewsletterContent(RichTextContent):
    form = NewsletterSectionAdminForm
    feincms_item_editor_form = NewsletterSectionAdminForm

    feincms_item_editor_includes = {
        'head': [ settings.PENNYBLACK_TINYMCE_CONFIG_URL ],
        }

    #text = models.TextField(_('text'), blank=True)

    class Meta:
        abstract = True
        verbose_name = _('text only')
        verbose_name_plural = _('text onlys')

    HREF_RE = re.compile(r'href\="([^"><]+)"')

    def replace_links(self, job):
        offset = 0
        for match in HREF_RE.finditer(self.text):
            replacelink = job.add_link(match.group(1))
            self.text = ''.join((self.text[:match.start(1)+offset], replacelink, self.text[match.end(1)+offset:]))
            offset += len(replacelink) - len(match.group(1))

    def render(self, **kwargs):
        # todo: hier template rendern
        # t=Template(self.text)
        # t.render(Context(hier noch den context des letters einfuegen))
        return mark_safe(self.text)
