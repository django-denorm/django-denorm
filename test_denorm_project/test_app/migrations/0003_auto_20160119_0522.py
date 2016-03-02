# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('test_app', '0003_auto_20160302_1706'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallCounter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('called_count', models.IntegerField(editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='CallCounterProxy',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('test_app.callcounter',),
        ),
    ]
