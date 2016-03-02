# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import denorm.fields


class Migration(migrations.Migration):

    dependencies = [
        ('test_app', '0003_auto_20160302_1706'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostExtend',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('author_name', models.CharField(editable=False, max_length=255)),
                ('post', models.OneToOneField(to='test_app.Post')),
            ],
        ),
        migrations.AlterField(
            model_name='forum',
            name='post_count',
            field=denorm.fields.CountField('post_set', default=0),
        ),
    ]
