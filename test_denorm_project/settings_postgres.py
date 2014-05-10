from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'denorm',
        'HOST': 'localhost',
        'USER': 'postgres',
        'PASSWORD': '',
    }
}
