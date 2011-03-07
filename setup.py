#!/usr/bin/python

from setuptools import setup, find_packages

setup(
    name='django-denorm',
    version='0.2.0',
    description='Denormalization magic for Django',
    long_description='django-denorm is a Django application to provide automatic management of denormalized database fields.',
    author='James Turnbull & Christian Schilling',
    author_email='james@incuna.com',
    url='http://github.com/incuna/django-denorm/',
    download_url='http://github.com/incuna/django-denorm/downloads',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development"
    ],
    packages=['denorm', 'denorm.db', 'denorm.db.mysql', 'denorm.db.postgresql', 'denorm.db.sqlite3', 'denorm.management', 'denorm.management.commands', 'denorm.tests'],
)