.. Pennyblack documentation master file, created by
   sphinx-quickstart on Sat Feb 12 00:41:24 2011.


Welcome to Pennyblack's documentation!
======================================

Penyblack is a newsletter module based on the feincms.org_ CMS building
toolkit. E-mails can either be sent as mass mails (e.g. monthly newsletter) or
as part of a customised workflow (e.g. user clicks on a link and in response to
that your application sends out an e-mail).  Conditional data and variables can
be filled in to a newsletter using the django template language.
SPF (sender validation) and bounce management can be activated if desired. Key
data like bounce rate, opening rate and link clicks is tracked and presented in
the admin menu. Sending bulk e-mails is easy on memory. 20’000 and more
addresses wont crash your server. From the outset we developed Pennyblack to
easily integrate into existing web projects.

.. _feincms.org: http://feincms.org

Contents:

.. toctree::
    :maxdepth: 2
   
    installation
    content
    bounce
    settings
    integration
    template
    models

Releases
========

.. toctree::
    :maxdepth: 1
    
    releases/0.3

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
