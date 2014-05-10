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
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_%s' % dbtype

    if os.system("cd test_denorm_project; nosetests --with-django"):
        exit(1)
