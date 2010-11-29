from django.core.management.base import BaseCommand, CommandError
from pennyblack.models import Sender

class Command(BaseCommand):
    args = ''
    help = 'Gets all Bounce emails'

    def handle(self, *args, **options):
        senders = Sender.objects.filter(get_bounce_emails=True)
        for sender in senders:
            sender.get_mail()
