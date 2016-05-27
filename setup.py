#!/usr/bin/python

from setuptools import setup

setup(
    name='django-denorm',
    version='0.3.3',
    description='Denormalization magic for Django',
    long_description='django-denorm is a Django application to provide automatic management of denormalized database fields.',
    author=', '.join((
        'Christian Schilling <initcrash@gmail.com>',
        'James Turnbull <james@incuna.com>',
    )),
    author_email='django-denorm@googlegroups.com',
    url='http://initcrash.github.com/django-denorm/',
    download_url='http://github.com/initcrash/django-denorm/downloads',
    install_requires=[
        'six',
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development"
    ],
    packages=[
        'denorm',
        'denorm.db',
        'denorm.db.mysql',
        'denorm.db.postgresql',
        'denorm.db.sqlite3',
        'denorm.management',
        'denorm.management.commands',
        'denorm.migrations',
    ],
)
