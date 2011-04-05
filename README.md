Allink Newsletter
=================

Installation
------------

**Notice**: This is a first draft of an installation guide. It's not finished
and complete.

0. Make sure you have a working django project setup.

0. Install Pennyblack over `pip`:

        pip install -e git://github.com/allink/pennyblack.git@b35c3597d42d810727af#egg=pennyblack-0.1.0-py2.6-develop

0. Make sure that the FeinCMS and Pennyblack Apps are added to your installed apps in your `settings.py`:

        'feincms',
        'feincms.module.medialibrary',
        'pennyblack',
        'pennyblack.module.subscriber',

0. Add a newsletter url to your `urls.py`:

        url(r'^newsletter/', include('pennyblack.urls'), name = 'pennyblack'),
    
0. Install dependencies (over `pip`):

    * pydns==2.3.4
    * pyspf==2.0.5
    
0. Import Pennyblack and add a newsletter template to your `models.py`:

        from pennyblack.models.newsletter import Newsletter
        from pennyblack.content.richtext import TextOnlyNewsletterContent, \
           TextWithImageNewsletterContent
       
        Newsletter.register_templates({
          'key': 'example',
          'title': 'Example Newsletter',
          'path': 'example_newsletter.html',
          'regions': (
              ('main', 'Main Region'),
              ),
          })

        Newsletter.create_content_type(TextOnlyNewsletterContent)
        Newsletter.create_content_type(TextWithImageNewsletterContent)
        
0. Add Pennyblack Models to south migration modules in your `settings.py`:

        SOUTH_MIGRATION_MODULES = {
            'pennyblack': 'checkbus_opening.migrations_pennyblack',
            'subscriber': 'checkbus_opening.migrations_subscriber',
        }
        
0. Run `schemamigrations` and `migrate`:

        ./manage.py schemamigration --initial pennyblack
        ./manage.py schemamigration --initial subscriber
        ./manage.py migrate
    

Dependencies
------------

*   Python
    *   django
    *   feincms
    *   pyspf
    *   pydns
    *   pil
*   Project Settings
    *   TEMPLATE_CONTEXT_PROCESSORS
        *   django.core.context_processors.request
    *   FEINCMS_ADMIN_MEDIA
    *   feincms medialibrary musst be installed