from django.conf import settings

TINYMCE_CONFIG_URL = getattr(settings, 'PENNYBLACK_TINYMCE_CONFIG_URL', 'admin/content/richtext/init.html')

LANGUAGES = getattr(settings, 'LANGUAGES')

JOB_STATUS = getattr(settings, 'PENNYBLACK_JOB_STATUS', ((1,'Draft'),(2,'Pending'),(3,'Sending'),(4,'Finished'),(5,'Error'),))