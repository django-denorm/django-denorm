from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'denorm_test',
        'HOST': 'localhost',
        'USER': 'postgres',
        'PASSWORD': '',
    }
}
