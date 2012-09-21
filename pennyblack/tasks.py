from datetime import timedelta

from celery.decorators import periodic_task
from celery.task import Task

from pennyblack import settings


@periodic_task(run_every=timedelta(minutes=settings.BOUNCE_DETECTION_GETMAIL_INTERVAL))
def pennyblack_get_email():
    """get bounced emails from the imap mailbox"""
    from pennyblack.models import Sender
    senders = Sender.objects.filter(get_bounce_emails=True)
    for sender in senders:
        sender.get_mail()


class SendJobTask(Task):
    def run(self, job_id):
        from pennyblack.models import Job
        j = Job.objects.get(id=job_id)
        j.send()
