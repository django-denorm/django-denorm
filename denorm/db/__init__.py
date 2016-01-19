from django.conf import settings

"""
This file attempts to automatically load the denorm backend for your chosen
database adaptor.

Currently only mysql, postgresql and sqlite3 are supported. If your database
is not detected then you can specify the backend in your settings file:

DATABASES = {
    'default': {
        'DENORM_BACKEND': 'denorm.db.postgresql',
    }
}
"""

# Default mappings from common postgresql equivalents
DB_GUESS_MAPPING = {
    'postgis': 'postgresql',
    'postgresql_psycopg2': 'postgresql',
}


def backend_for_dbname(db_name):
    return 'denorm.db.%s' % DB_GUESS_MAPPING.get(db_name, db_name)

from django.db import connections, DEFAULT_DB_ALIAS
if 'DENORM_BACKEND' in connections[DEFAULT_DB_ALIAS].settings_dict:
    backend = connections[DEFAULT_DB_ALIAS].settings_dict['DENORM_BACKEND']
else:
    engine = connections[DEFAULT_DB_ALIAS].settings_dict['ENGINE']
    backend = backend_for_dbname(engine.rsplit(".", 1)[1])

try:
    triggers = __import__('.'.join([backend, 'triggers']), {}, {}, [''])
except ImportError:
    raise ImportError("""There is no django-denorm database module for the engine '%s'. Please either choose a supported one, or remove 'denorm' from INSTALLED_APPS.\n""" % backend)
