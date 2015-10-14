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

    test_label = sys.argv[2] if len(sys.argv) > 2 else "test_app"
    if os.system("cd test_denorm_project; python -Wall manage.py test %s" % test_label):
        exit(1)
