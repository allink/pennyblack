from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from newsletter.models import Newsletter, NewsletterLink, NewsletterMail

def preview(request, newsletter_id):
    """
    Previews this newsletter as a Website
    """
    newsletter = Newsletter.objects.filter(pk=newsletter_id)[0]
    return render_to_response(newsletter.template.path, {
        'newsletter' : newsletter,
        }, context_instance=RequestContext(request))

def redirect_link(request, mail_hash, link_hash):
    """
    Redirects to the link target and marks this mail as read
    """
    NewsletterLink.objects.filter(link_hash=link_hash).update(click_count=F('click_count')+1)
    NewsletterMail.objects.filter(mail_hash=mail_hash).update(viewed=True)
