# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction


@transaction.atomic
def drop_duplicates(apps, schema_editor):
    # We should leave only unique dirty objects
    DirtyInstance = apps.get_model('denorm', 'DirtyInstance')
    if DirtyInstance.objects.count() > 100000:
    	raise ValueError("You should clear DirtyInstances table first")
    distinct = DirtyInstance.objects.distinct('object_id', 'content_type')
    DirtyInstance.objects.exclude(id__in=distinct).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('denorm', '0002_auto_20160525_2242'),
    ]

    operations = [
        migrations.RunPython(drop_duplicates, reverse_code=migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='dirtyinstance',
            unique_together=set([('content_type', 'object_id')]),
        ),
    ]
