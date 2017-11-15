# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import denorm.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DenormModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('ham', models.TextField(editable=False)),
                ('spam', models.TextField(editable=False)),
            ],
            options={
                'abstract': False,
                'swappable': 'DENORM_MODEL',
            },
        ),
        migrations.CreateModel(
            name='RealDenormModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('ham', models.TextField(editable=False)),
                ('eggs', models.TextField(editable=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cachekey', denorm.fields.CacheKeyField(default=0, editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CachedModelA',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cached_data', denorm.fields.CachedField(default=0, editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CachedModelB',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('data', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FailingTriggersModelA',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.SmallIntegerField(default=0)),
                ('SomeWeirdName', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FailingTriggersModelB',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('SomeWeirdName', models.TextField(editable=False)),
                ('a', models.ForeignKey(to='test_app.FailingTriggersModelA', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Forum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tags_string', models.TextField(editable=False)),
                ('title', models.CharField(max_length=255)),
                ('post_count', denorm.fields.CountField(b'post_set', default=0)),
                ('cachekey', denorm.fields.CacheKeyField(default=0, editable=False)),
                ('author_names', models.CharField(max_length=255, editable=False)),
                ('path', models.TextField(editable=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('cachekey', denorm.fields.CacheKeyField(default=0, editable=False)),
                ('full_name', models.CharField(max_length=255, editable=False)),
                ('bookmark_titles', models.TextField(null=True, editable=False, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tags_string', models.TextField(editable=False)),
                ('title', models.CharField(max_length=255, blank=True)),
                ('forum_title', models.CharField(max_length=255, editable=False)),
                ('author_name', models.CharField(max_length=255, editable=False)),
                ('response_count', models.PositiveIntegerField(editable=False)),
                ('author', models.ForeignKey(blank=True, to='test_app.Member', null=True, on_delete=models.CASCADE)),
                ('forum', models.ForeignKey(blank=True, to='test_app.Forum', null=True, on_delete=models.CASCADE)),
                ('response_to', models.ForeignKey(related_name='responses', blank=True, to='test_app.Post', null=True, on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SkipCommentWithAttributeSkip',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True, null=True)),
                ('post_text', models.TextField(editable=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SkipCommentWithoutSkip',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True, null=True)),
                ('post_text', models.TextField(editable=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SkipCommentWithSkip',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True, null=True)),
                ('post_text', models.TextField(editable=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SkipPost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='skipcommentwithskip',
            name='post',
            field=models.ForeignKey(to='test_app.SkipPost', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='skipcommentwithoutskip',
            name='post',
            field=models.ForeignKey(to='test_app.SkipPost', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='skipcommentwithattributeskip',
            name='post',
            field=models.ForeignKey(to='test_app.SkipPost', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='member',
            name='bookmarks',
            field=models.ManyToManyField(to='test_app.Post', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='forum',
            name='authors',
            field=models.ManyToManyField(to='test_app.Member', null=True, editable=False, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='forum',
            name='parent_forum',
            field=models.ForeignKey(blank=True, to='test_app.Forum', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cachedmodela',
            name='b',
            field=models.ForeignKey(to='test_app.CachedModelB', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='attachment',
            name='forum',
            field=models.ForeignKey(blank=True, editable=False, to='test_app.Forum', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='attachment',
            name='post',
            field=models.ForeignKey(blank=True, to='test_app.Post', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
