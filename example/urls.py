from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
admin.autodiscover()

urlpatterns = patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
    
    (r'^admin/', include(admin.site.urls)),
    
    url(r'^newsletter/', include('pennyblack.urls'), name = 'pennyblack'),
)
