from pennyblack.module.subscriber.models import NewsletterSubscriber, SubscriberGroup

def add_subscriber(email,groups=[], **kwargs):
    """
    Adds a subscriber to the given groups
    """
    subscriber = NewsletterSubscriber.objects.get_or_add(email)
    for group_name in groups:
        group = SubscriberGroup.objects.get_or_add(group_name)
        if group not in subscriber.groups.all():
            subscriber.groups.add(group)