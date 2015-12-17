from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'denorm_test',
        'HOST': 'localhost',
        'USER': 'postgres',
        'PASSWORD': '',
    }
}
