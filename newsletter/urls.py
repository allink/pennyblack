from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^link/(?P<mail_hash>[a-z0-9]+)/(?P<link_hash>[a-z0-9]+)/$', 'newsletter.views.redirect_link', name='newsletter.redirect_link'),
    url(r'^preview/(?P<newsletter_id>\d+)/$', 'newsletter.views.preview', name='newsletter.preview'),
)
