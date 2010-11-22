from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    args = ''
    help = 'Sends all pending Newsletters'

    def handle(self, *args, **options):
        self.stdout.write('Send mails')
