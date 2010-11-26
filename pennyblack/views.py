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
    Link.objects.filter(link_hash=link_hash).update(click_count=F('click_count')+1)
    Mail.objects.filter(mail_hash=mail_hash).update(viewed=True)
    try:
        link = Link.objects.get(link_hash=link_hash)
        return HttpResponseRedirect(link.link_target)
    except ObjectDoesNotExist:
        return HttpResponseRedirect('/')
    

def ping(request, mail_hash, filename):
    mail = Mail.objects.filter(mail_hash=mail_hash)
    if mail.count()>0:
        mail = mail[0]
        mail.viewed=True
        mail.save()
    return HttpResponseRedirect(mail.job.newsletter.header_image.get_absolute_url())


def view(request, mail_hash):
    mail = Mail.objects.filter(mail_hash=mail_hash)
    if mail.count() != 1:
        return HttpResponseRedirect('/')
    mail=mail[0]
    mail.viewed=True
    mail.save()
    return HttpResponse(mail.get_content(webview=True))
