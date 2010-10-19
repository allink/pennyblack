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
    packages=['pennyblack', 'pennyblack.conf', 'pennyblack.content'],
    package_data={'pennyblack':'templates/*.html'},
    classifiers=[
        'Development Status :: 1 - Planning',
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
        'FeinCMS(>=1.1.4)',
        'Django(>=1.2.1)',
        'pydns',
        'pyspf',
    ],
    
)