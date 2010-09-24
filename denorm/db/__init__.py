from django.conf import settings

if hasattr(settings, 'DATABASE_DENORM_BACKEND'):
    backend = settings.DATABASE_DENORM_BACKEND
if hasattr(settings, 'DATABASE_ENGINE') and settings.DATABASE_ENGINE:
    backend = settings.DATABASE_ENGINE
else:
    # Assume Django 1.2
    DB_MAPPING = {'postgis':'postgresql',
                  'postgresql_psycopg2':'postgresql',
                 }
    from django.db import connections, DEFAULT_DB_ALIAS
    if 'DENORM_BACKEND' in connections[DEFAULT_DB_ALIAS].settings_dict:
        backend = connections[DEFAULT_DB_ALIAS].settings_dict['DENORM_BACKEND']
    else:
        engine = connections[DEFAULT_DB_ALIAS].settings_dict['ENGINE']
        backend = engine.rsplit(".", 1)[1]
        backend = DB_MAPPING.get(backend, backend)

triggers_module_name = ['denorm.db', backend, 'triggers']
try:
    triggers = __import__('.'.join(triggers_module_name),{},{},[''])
except ImportError:
    raise ImportError("There is no django-denorm database module for the engine '%s'. Please either choose a supported one, or remove 'denorm' from INSTALLED_APPS.\n" % backend)


