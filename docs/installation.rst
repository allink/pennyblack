Installation
============
This document describes the steps needed to set up pennyblack in your own project.

Since pennyblack is based on FeinCMS, you'll need a FeinCMS installation first.

You can also install pennyblack using pip like so::

    $ pip install pennyblack

Or you can grab your own copy of the pennyblack source from github::

    $ git clone git://github.com/allink/pennyblack.git

Some features like spf detection need pyspf and pydns installations.

Make sure that the FeinCMS and pennyblack Apps are added to installed apps in
the `settings.py`::

    'feincms',
    'feincms.module.medialibrary',
    'pennyblack',

Add a newsletter url to the `urls.py`::

    url(r'^newsletter/', include('pennyblack.urls'), name = 'pennyblack'),

Cronjob
-------
To send emails and receive bounced emails these to management commands have to
be executed::

    ./manage.py sendmail
    ./manage.py getmail


Configuration
=============

To use pennyblacks newsletter model, you need to register html templates and
content types like you do for the FeinCMS page module. Simple newsletter with
only text content would look like this::

    from pennyblack.models import Newsletter
    from pennyblack.content.richtext import TextOnlyNewsletterContent

    Newsletter.register_templates({
        'key': 'base',
        'title': 'Generic Newsletter',
        'path': 'pennyblack/base_newsletter.html',
        'regions': (
            ('main', 'Main Region'),
            ),
        })

    Newsletter.create_content_type(TextOnlyNewsletterContent)

South Migrations
================

To use south migrations specify a south migration module in the settings::
    
    SOUTH_MIGRATION_MODULES = {
        'pennyblack': 'project_name.migrations_pennyblack',
    }
    
    