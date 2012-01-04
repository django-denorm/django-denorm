from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # 'NAME': ':memory:',
        'NAME': 'test_project.db',
    }
}
