from feincms.content.richtext.models import RichTextContent
from django.utils.safestring import mark_safe

import re
import itertools

def render(self, **kwargs):
    return mark_safe(self.text)

setattr(RichTextContent, 'render', render)

HREF_RE = re.compile(r'href\="([^"><]+)"')

def replace_links(self, job):
    offset = 0
    for match in HREF_RE.finditer(self.text):
        replacelink = job.add_link(match.group(1))
        self.text = ''.join((self.text[:match.start(1)+offset], replacelink, self.text[match.end(1)+offset:]))
        offset += len(replacelink) - len(match.group(1))

setattr(RichTextContent, 'replace_links', replace_links)