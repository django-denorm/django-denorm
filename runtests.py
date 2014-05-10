#!/usr/bin/python
import sys
import os

try:
    dbtypes = [sys.argv[1]]
except:
    dbtypes = ['sqlite', 'mysql', 'postgres']

os.environ['PYTHONPATH'] = '.:..'

for dbtype in dbtypes:
    print 'running tests on', dbtype
    os.environ['DJANGO_SETTINGS_MODULE'] = 'test_denorm_project.settings_%s' % dbtype

    if os.system("cd test_denorm_project; python manage.py test test_app"):
        exit(1)
