from django.conf import settings

if hasattr(settings, 'DATABASE_ENGINE') and settings.DATABASE_ENGINE:
    backend = settings.DATABASE_ENGINE
else:
    # Assume Django 1.2
    from django.db import connections, DEFAULT_DB_ALIAS
    engine = connections[DEFAULT_DB_ALIAS].settings_dict['ENGINE']
    backend = engine.rsplit(".", 1)[1]

triggers_module_name = ['denorm.db', backend, 'triggers']
try:
    triggers = __import__('.'.join(triggers_module_name),{},{},[''])
except ImportError:
    raise ImportError("There is no django-denorm database module for the engine '%s'. Please either choose a supported one, or remove 'denorm' from INSTALLED_APPS.\n" % backend)


