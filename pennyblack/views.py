from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from pennyblack.models import Newsletter, Link, Mail

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
    return render_to_response(newsletter.template.path, request.content_context, context_instance=RequestContext(request))
    

def redirect_link(request, mail_hash, link_hash):
    """
    Redirects to the link target and marks this mail as read
    """
    try:
        mail = Mail.objects.get(mail_hash=mail_hash)
        link = Link.objects.get(link_hash=link_hash)
    except ObjectDoesNotExist:
        return HttpResponseRedirect('/')
    mail.on_landing(request)
    return HttpResponseRedirect(link.click(mail))
    

def ping(request, mail_hash, filename):
    try:
        mail = Mail.objects.get(mail_hash=mail_hash)
    except ObjectDoesNotExist:
        HttpResponseRedirect('/')
    mail.mark_viewed()
    return HttpResponseRedirect(mail.job.newsletter.header_image.get_absolute_url())


def view(request, mail_hash):
    try:
        mail = Mail.objects.get(mail_hash=mail_hash)
    except ObjectDoesNotExist:
        return HttpResponseRedirect('/')
    mail.mark_viewed()
    return HttpResponse(mail.get_content(webview=True))
