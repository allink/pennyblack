from django.contrib import admin

from pennyblack import settings
from pennyblack.models.newsletter import Newsletter, NewsletterAdmin
from pennyblack.models.job import Job, JobAdmin
from pennyblack.models.sender import Sender, SenderAdmin

admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(Job,JobAdmin)
admin.site.register(Sender,SenderAdmin)