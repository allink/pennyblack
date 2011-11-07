Template
========

Since pennyblack is heavily based on the feincms base model, you have to
register at least one template to use it. There is a example template called
base_newsletter.html in the templates folder which you could register like
shown in the example project.

::

    from pennyblack.models import Newsletter
    
    Newsletter.register_templates({
        'key': 'base',
        'title': 'Generic Newsletter',
        'path': 'base_newsletter.html',
        'regions': (
            ('main', 'Main Region'),
            ),
        })
        
Context
=======

By default the template context in emails is as follows:

person: person object
group_object: corresponding group (only if available)
mail: the mail object
base_url: base url

