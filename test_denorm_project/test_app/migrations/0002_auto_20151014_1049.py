# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import denorm.fields


class Migration(migrations.Migration):

    dependencies = [
        ('test_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FilterCountItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active', models.BooleanField(default=False)),
                ('text', models.CharField(default=b'', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='FilterCountModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active_item_count', denorm.fields.CountField(b'items', default=0)),
            ],
        ),
        migrations.CreateModel(
            name='FilterSumItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('age', models.IntegerField(default=18)),
                ('active_item_count', models.PositiveIntegerField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='FilterSumModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active_item_sum', denorm.fields.SumField(b'counts', default=0)),
            ],
        ),
        migrations.AddField(
            model_name='filtersumitem',
            name='parent',
            field=models.ForeignKey(related_name='counts', to='test_app.FilterSumModel', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='filtercountitem',
            name='parent',
            field=models.ForeignKey(related_name='items', to='test_app.FilterCountModel', on_delete=models.CASCADE),
        ),
    ]
