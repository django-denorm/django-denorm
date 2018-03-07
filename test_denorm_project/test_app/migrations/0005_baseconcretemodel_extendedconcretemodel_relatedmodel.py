# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import denorm.fields


class Migration(migrations.Migration):

    dependencies = [
        ('test_app', '0004_auto_20160306_1822'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseConcreteModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExtendedConcreteModel',
            fields=[
                ('baseconcretemodel_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='test_app.BaseConcreteModel')),
                ('item_count', denorm.fields.CountField(b'relatedmodel_set', default=0)),
            ],
            options={
            },
            bases=('test_app.baseconcretemodel',),
        ),
        migrations.CreateModel(
            name='RelatedModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('thing', models.ForeignKey(to='test_app.ExtendedConcreteModel')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
