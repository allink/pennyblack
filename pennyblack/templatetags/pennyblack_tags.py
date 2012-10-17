import hashlib

from django import template
from django.core.urlresolvers import reverse

from pennyblack.models import Link

register = template.Library()


class NewsletterstyleNode(template.Node):
    def __init__(self, key, style, request):
        self.key = key
        self.style = style
        self.request_var = template.Variable(request)

    def render(self, context):
        request = self.request_var.resolve(context)
        if not hasattr(request, '_pennyblack_newsletterstyle'):
            setattr(request, '_pennyblack_newsletterstyle', dict())
        request._pennyblack_newsletterstyle[str(self.key)] = self.style.render(context)
        return ''


def newsletterstyle(parser, token):
    """
    Stores the content in your context
    {% newsletterstyle request text_only_content %}
    """
    bits = list(token.split_contents())
    if len(bits) != 3:
        raise template.TemplateSyntaxError("%r expected format is 'newsletterstyle request stylename'" % bits[0])
    request = bits[1]
    key = parser.compile_filter(bits[2])
    style = parser.parse(('endnewsletterstyle',))
    parser.delete_first_token()
    return NewsletterstyleNode(key, style, request)
newsletterstyle = register.tag(newsletterstyle)


class NewsletterGetStyleNode(template.Node):
    def __init__(self, key, request):
        self.key = key
        self.request_var = template.Variable(request)

    def render(self, context):
        request = self.request_var.resolve(context)
        if not hasattr(request, '_pennyblack_newsletterstyle'):
            return ''
        if str(self.key) not in request._pennyblack_newsletterstyle.keys():
            return ''
        return request._pennyblack_newsletterstyle[str(self.key)]


def get_newsletterstyle(parser, token):
    """
    Loads a stored style and renders it
    """
    bits = list(token.split_contents())
    if len(bits) != 3:
        raise template.TemplateSyntaxError("%r expected format is 'newsletterstyle request stylename'" % bits[0])
    request = bits[1]
    key = parser.compile_filter(bits[2])
    return NewsletterGetStyleNode(key, request)
get_newsletterstyle = register.tag(get_newsletterstyle)


class NewsletterHeaderImageNode(template.Node):
    def __init__(self, extra_args={}):
        self.extra_args = extra_args

    def render(self, context):
        newsletter = context['newsletter']
        if context['webview']:
            if 'mail' in context:
                mail = context['mail']
                header_url = mail.get_header_url()
            else:
                header_url = ''
            header_image = newsletter.header_image.get_absolute_url()
        else:
            mail = context['mail']
            header_url = mail.get_header_url()
            header_image = newsletter.get_base_url() + reverse('pennyblack.ping', kwargs={'mail_hash': mail.mail_hash, 'filename': newsletter.header_image})
        return """<a href="%s" target="_blank"><img src="%s" border="0" %s/></a>""" % (header_url, header_image, ' '.join(self.extra_args))


@register.tag
def header_image(parser, token):
    """
    Renders the header image with tracking any extra args are given to the img tag

    {% header_image alt="Header" width="283" height="157" align="left" vspace="0" hspace="0" border="0" %}

    renders

    <a href="" target="_blank"><img src="link to the image" border="0" alt="Header" width="283" height="157" align="left" vspace="0" hspace="0" border="0"/></a>
    """
    bits = list(token.split_contents())
    extra_args = []
    for bit in bits:
        splitted = bit.split('=')
        if len(splitted) == 2:
            extra_args.append(bit)
    return NewsletterHeaderImageNode(extra_args=extra_args)


class NewsletterLinkUrlNode(template.Node):
    def __init__(self, identifier=None):
        self.identifier = identifier

    def render(self, context):
        from pennyblack.models import Newsletter
        if 'mail' not in context:
            return u'#'
        mail = context['mail']
        newsletter = mail.job.newsletter
        if newsletter.is_workflow():
            job = newsletter.get_default_job()
        else:
            job = mail.job
        try:
            link = job.links.get(identifier=self.identifier)
        except job.links.model.DoesNotExist:
            link = Newsletter.add_view_link_to_job(self.identifier, job)
        return context['base_url'] + reverse('pennyblack.redirect_link', args=(mail.mail_hash, link.link_hash))


@register.tag
def link_url(parser, token):
    """
    Renders a link wich is provided by the group object.
    """
    bits = list(token.split_contents())
    if len(bits) != 2:
        raise template.TemplateSyntaxError("%r expected format is 'link_url url_identifier'" % bits[0])
    return NewsletterLinkUrlNode(identifier=bits[1])


class ContentImageUrlNode(template.Node):
    def __init__(self, identifier=None):
        self.identifier = identifier

    def render(self, context):
        kwargs = {}
        if 'mail' in context:
            kwargs['context'] = context
        if self.identifier:
            kwargs['identifier'] = self.identifier
        return context['content'].get_image_url(**kwargs)


@register.tag
def content_image_url(parser, token):
    """
    Renders the link of the given content.
    """
    bits = list(token.split_contents())
    if len(bits) == 2:
        return ContentImageUrlNode(identifier=bits[1])
    return ContentImageUrlNode()


class LinkTagNode(template.Node):
    def __init__(self, target, token):
        self.target = target
        self.token = token

    def render(self, context):
        if isinstance(self.token, template.Variable):
            self.token = self.token.resolve(context)
        target = self.target.resolve(context)
        if 'mail' not in context:
            return "%s %s " % (target, self.token)
        mail = context['mail']
        link, created = Link.objects.get_or_create(token=self.token, job=mail.job)
        if created:
            link.link_target = target
            link.save()
        return context['base_url'] + reverse('pennyblack.redirect_link', args=(mail.mail_hash, link.link_hash))


@register.tag
def trackable_link(parser, token):
    """
    Renders a url that can be used to track links in a template outside the
    content types. Multiple links can be grouped together by giving a third
    parameter which identifies the link. This makes it possible to group links
    like in the following example:
    {% if random %}
        <a href="{% trackable_link 'https://github.com/allink/pennyblack' 'aaaaaaaaaa' %}" class="special">link</a>
    {% else %}
        <a href="{% trackable_link 'https://github.com/allink/pennyblack' 'aaaaaaaaaa' %}">link</a>
    {% endif %}
    The target link can contain template variables in the following form:
    <a href="{% trackable_link '{{base_url}}' 'aaaaaaaaaa' %}">link</a>
    """
    bits = list(token.split_contents())
    if not 2 <= len(bits) <= 3:
        raise template.TemplateSyntaxError("%r expected format is 'tackable_link 'http://target_url''" % bits[0])
    if len(bits) == 2:
        template_loader, (position_start, position_end) = parser.command_stack[0][-1]
        link_token = hashlib.md5("%s%s" % (template_loader.loadname, position_start)).hexdigest()
    else:
        link_token = template.Variable(bits[2])
    return LinkTagNode(template.Variable(bits[1]), link_token)
