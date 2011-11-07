VERSION = (0, 3, 2)
__version__ = '.'.join(map(str, VERSION))

# Do not use Django settings at module level as recommended
try:
    from django.utils.functional import LazyObject
except ImportError:
    pass
else:
    class LazySettings(LazyObject):
        def _setup(self):
            from pennyblack import default_settings
            self._wrapped = Settings(default_settings)

    class Settings(object):
        def __init__(self, settings_module):
            for setting in dir(settings_module):
                if setting == setting.upper():
                    setattr(self, setting, getattr(settings_module, setting))

    settings = LazySettings()

def send_newsletter(newsletter_name, *args, **kwargs):
    """
    Gets a newsletter by its name and tries to send it to receiver
    """
    from pennyblack.models import Newsletter
    newsletter = Newsletter.objects.get_workflow_newsletter_by_name(newsletter_name)
    if newsletter:
        newsletter.send(*args, **kwargs)