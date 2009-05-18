from django.conf import settings

triggers_module_name = ['denorm.db', settings.DATABASE_ENGINE,'triggers']
try:
    triggers = __import__('.'.join(triggers_module_name),{},{},[''])
except ImportError:
    raise ImportError("There is no django-denorm database module for the engine '%s'. Please either choose a supported one, or remove 'denorm' from INSTALLED_APPS.\n" % settings.DATABASE_ENGINE)


