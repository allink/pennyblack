Installation
============
This document describes the steps needed to set up pennyblack in your own project.

Since pennyblack is based on FeinCMS, you'll need a FeinCMS installation first.

You can also install pennyblack using pip like so::

    $ pip install pennyblack

Or you can grab your own copy of the pennyblack source from github::

    $ git clone git://github.com/allink/pennyblack.git

Some features like spf detection need pyspf and pydns installations.

Configuration
=============

To use pennyblacks newsletter model, you need to register html templates and content types like you do for the FeinCMS page module. Simple newsletter with only text content would look like this::

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
    