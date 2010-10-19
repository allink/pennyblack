from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^link/(?P<mail_hash>[a-z0-9]+)/(?P<link_hash>[a-z0-9]+)/$', 'pennyblack.views.redirect_link', name='newsletter.redirect_link'),
    url(r'^preview/(?P<newsletter_id>\d+)/$', 'pennyblack.views.preview', name='pennyblack.preview'),
    url(r'^view/(?P<mail_hash>\w+)', 'pennyblack.views.view', name='pennyblack.view'),
    url(r'^ping/(?P<mail_hash>\w+)/(?P<path>.*)$', 'pennyblack.views.ping', name='pennyblack.ping'),
    url(r'^landing/(?P<mail_hash>\w+)', 'pennyblack.views.landing', name='pennyblack.landing'),
    
)
