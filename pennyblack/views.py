import types
from urlparse import urlparse, urlunparse, parse_qs
from urllib import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.functional import wraps

from pennyblack.models import Newsletter, Link, Mail, Job


def needs_mail(function):
    """
    Decorator to get the mail object
    """
    @wraps(function)
    def wrapper(request, mail_hash=None, *args, **kwargs):
        try:
            mail = Mail.objects.get(mail_hash=mail_hash)
        except ObjectDoesNotExist:
            return HttpResponseRedirect('/')
        return function(request, mail=mail, *args, **kwargs)
    return wrapper


def needs_link(function):
    """
    Decorator to get the link object
    """
    @wraps(function)
    def wrapper(request, link_hash=None, *args, **kwargs):
        try:
            link = Link.objects.get(link_hash=link_hash)
        except ObjectDoesNotExist:
            return HttpResponseRedirect('/')
        return function(request, link=link, *args, **kwargs)
    return wrapper


@login_required
def preview(request, newsletter_id):
    """
    Previews this newsletter as a Website
    """
    newsletter = Newsletter.objects.filter(pk=newsletter_id)[0]
    request.content_context = {
        'newsletter': newsletter,
        'webview': True,
    }
    job_id = request.GET.get('job', None)
    if job_id:
        job = get_object_or_404(Job, pk=job_id)
        if job.mails.count():
            mail = job.mails.all()[0]
            request.content_context.update(mail.get_context())
            request.content_context.update({'base_url': ''})
    return render_to_response(newsletter.template.path, request.content_context, context_instance=RequestContext(request))


@needs_mail
@needs_link
def redirect_link(request, mail, link):
    """
    Redirects to the link target and marks this mail as read. If the link
    belongs to a proxy view it redirects it to the proxy view url.
    """
    mail.on_landing(request)
    target = link.click(mail)
    if isinstance(target, types.FunctionType):
        return HttpResponseRedirect(reverse('pennyblack.proxy', args=(mail.mail_hash, link.link_hash)))
    # disassemble the url
    scheme, netloc, path, params, query, fragment = tuple(urlparse(target))
    if scheme in ('http', 'https'):  # insert ga tracking if scheme is appropriate
        parsed_query = parse_qs(query)
        if mail.job.newsletter.utm_source:
            parsed_query['utm_source'] = mail.job.newsletter.utm_source
        if mail.job.newsletter.utm_medium:
            parsed_query['utm_medium'] = mail.job.newsletter.utm_medium
        if mail.job.utm_campaign:
            parsed_query['utm_campaign'] = mail.job.utm_campaign
        query = urlencode(parsed_query, True)
    # reassemble the url
    target = urlunparse((scheme, netloc, path, params, query, fragment))
    response = HttpResponseRedirect(target)
    try:
        response.allowed_schemes = response.allowed_schemes + ['mailto']
    except AttributeError:
        pass
    return response


@needs_mail
def ping(request, mail, filename):
    mail.mark_viewed()
    return HttpResponseRedirect(mail.job.newsletter.header_image.get_absolute_url())


@needs_mail
def view(request, mail):
    mail.mark_viewed()
    return HttpResponse(mail.get_content(webview=True))


@needs_mail
@needs_link
def proxy(request, mail, link):
    return link.get_target(mail)(request, mail.person, mail.job.group_object)
