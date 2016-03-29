# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('denorm', '0002_dirtyinstance_identifier'),
    ]

    operations = [
        migrations.AddField(
            model_name='dirtyinstance',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2016, 3, 29, 19, 28, 20, 943768), auto_now_add=True),
            preserve_default=False,
        ),
    ]
