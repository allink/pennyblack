from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.functional import wraps

from pennyblack.models import Newsletter, Link, Mail, Job

import types

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
        'newsletter' : newsletter,
        'webview' : True,
        }
    job_id = request.GET.get('job',None)
    if job_id:
        job = get_object_or_404(Job, pk=job_id)
        if job.mails.count():
            mail = job.mails.all()[0]
            request.content_context.update(mail.get_context())
            request.content_context.update({'base_url':''})
    return render_to_response(newsletter.template.path, request.content_context, context_instance=RequestContext(request))
    
@needs_mail
@needs_link
def redirect_link(request, mail, link):
    """
    Redirects to the link target and marks this mail as read
    """
    mail.on_landing(request)
    target = link.click(mail)
    if isinstance(target, types.FunctionType):
        return HttpResponseRedirect(reverse('pennyblack.proxy', args=(mail.mail_hash, link.link_hash)))
    ga_tracking = "utm_source=%s&utm_medium=%s&utm_campaign=%s" % (
        mail.job.newsletter.utm_source, mail.job.newsletter.utm_medium,
        mail.job.utm_campaign)
    if target.find('?') > 0:
        target = '%s&%s' % (target, ga_tracking)
    else:
        target = '%s?%s' % (target, ga_tracking)
    return HttpResponseRedirect(target)
    
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
