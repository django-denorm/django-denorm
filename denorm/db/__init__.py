from django.conf import settings

"""
This file attempts to automatically load the denorm backend for your chosen
database adaptor.

Currently only mysql, postgresql and sqlite3 are supported. If your database
is not detected then you can specify the backend in your settings file:

# Django < 1.2
DATABASE_DENORM_BACKEND = 'denorm.db.postgresql'

# Django >= 1.2
DATABASES = {
    'default': {
        'DENORM_BACKEND': 'denorm.db.postgresql',
    }
}
"""

# Default mappings from common postgresql equivalents
DB_GUESS_MAPPING = {
    'postgis':'postgresql',
    'postgresql_psycopg2':'postgresql',
 }

def backend_for_dbname(db_name):
    return 'denorm.db.%s' % DB_GUESS_MAPPING.get(db_name, db_name)

if hasattr(settings, 'DATABASE_ENGINE') and settings.DATABASE_ENGINE:
    # Django < 1.2 syntax
    if hasattr(settings, 'DATABASE_DENORM_BACKEND'):
        backend = settings.DATABASE_DENORM_BACKEND
    else:
        backend = backend_for_dbname(settings.DATABASE_ENGINE)
        
else:
    # Assume >= Django 1.2 syntax
    from django.db import connections, DEFAULT_DB_ALIAS
    if 'DENORM_BACKEND' in connections[DEFAULT_DB_ALIAS].settings_dict:
        backend = connections[DEFAULT_DB_ALIAS].settings_dict['DENORM_BACKEND']
    else:
        engine = connections[DEFAULT_DB_ALIAS].settings_dict['ENGINE']
        backend = backend_for_dbname(engine.rsplit(".", 1)[1])

try:
    triggers = __import__('.'.join([backend, 'triggers']),{},{},[''])
except ImportError:
    raise ImportError("""There is no django-denorm database module for the engine '%s'. Please either choose a supported one, or remove 'denorm' from INSTALLED_APPS.\n""" % backend)