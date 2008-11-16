
from django.contrib import admin

from gallery import models

admin.site.register(models.Picture)
admin.site.register(models.Gallery)
