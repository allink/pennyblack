from django.contrib import admin

from pennyblack import settings
from pennyblack.models.newsletter import Newsletter, NewsletterAdmin
from pennyblack.models.job import Job, JobAdmin, JobStatistic, JobStatisticAdmin
from pennyblack.models.sender import Sender, SenderAdmin

admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(Job,JobAdmin)
admin.site.register(JobStatistic, JobStatisticAdmin)
admin.site.register(Sender,SenderAdmin)