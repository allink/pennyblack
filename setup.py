#! /usr/bin/env python
from setuptools import setup

import pennyblack
setup(
    name='pennyblack',
    version = pennyblack.__version__,
    description = 'django based newsletter toolkit',
    author = 'Marc Egli',
    author_email = 'egli@allink.ch',
    url = 'http://github.com/allink/pennyblack/',
    packages=[
        'pennyblack',
        'pennyblack.content',
        'pennyblack.management',
        'pennyblack.management.commands',
        'pennyblack.models',
        'pennyblack.module.subscriber',
        'pennyblack.templatetags',
    ],
    package_data={'pennyblack':'templates/*.html'},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Communications :: Email',
    ],
    requires=[
        'FeinCMS(>=1.2.1)',
        'Django(>=1.2.1)',
        'pydns',
        'pyspf',
        'pil',
    ],
    
)