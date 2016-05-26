# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction


class Migration(migrations.Migration):

    dependencies = [
        ('denorm', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dirtyinstance',
            name='object_id',
            field=models.TextField(db_index=True, null=True, blank=True),
        ),
    ]
