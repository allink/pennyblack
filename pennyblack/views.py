from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from pennyblack.models import Newsletter, NewsletterLink, NewsletterMail

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

def ping(request, mail_hash, path):
    mail = NewsletterMail.objects.filter(mail_hash=mail_hash)
    if mail.count()>0:
        mail = mail[0]
        mail.viewed=True
        mail.save()
    return HttpResponseRedirect(settings.NEWSLETTER_URL + path)


def view(request, mail_hash):
    mail = NewsletterMail.objects.filter(mail_hash=mail_hash)
    if mail.count() != 1:
        return HttpResponseRedirect('/')
    mail=mail[0]
    mail.viewed=True
    mail.save()
    return HttpResponse(mail.get_context())


def landing(request, mail_hash):
    mail = NewsletterMail.objects.filter(mail_hash=mail_hash)
    if mail.count() != 1:
        return HttpResponseRedirect('/')
    mail = mail[0]
    if type(mail.person) == type(Customer()):
        mail.person.done=True
        mail.person.save()
        request.session['customer_id'] = mail.person.id
        link = '/#!/' + settings.EVENTS_PAGE_URL[translation.get_language()] + '/' + str(mail.job.group.event.id) + '/'
        return HttpResponseRedirect(link)        
    return HttpResponseRedirect('/')
