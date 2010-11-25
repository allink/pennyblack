from django.core.management.base import BaseCommand, CommandError
from pennyblack.models import NewsletterJob
from pennyblack import settings

class Command(BaseCommand):
    args = ''
    help = 'Sends all pending Newsletters'

    def handle(self, *args, **options):
        pending_jobs = NewsletterJob.objects.filter(status__in=settings.JOB_STATUS_PENDING)
        for job in pending_jobs:
            job.send()
            print str(job)+ ' sent'