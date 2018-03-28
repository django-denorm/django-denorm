# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import denorm.fields


class Migration(migrations.Migration):

    dependencies = [
        ('test_app', '0002_auto_20151014_1049'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallCounter',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('called_count', models.IntegerField(editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='PostExtend',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('author_name', models.CharField(editable=False, max_length=255)),
                ('post', models.OneToOneField(to='test_app.Post', on_delete=models.CASCADE)),
            ],
        ),
        migrations.AlterField(
            model_name='forum',
            name='authors',
            field=models.ManyToManyField(editable=False, blank=True, to='test_app.Member'),
        ),
        migrations.AlterField(
            model_name='forum',
            name='post_count',
            field=denorm.fields.CountField('post_set', default=0),
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
