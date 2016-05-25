# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction


@transaction.atomic
def drop_duplicates(apps, schema_editor):
    # We should leave only unique dirty objects
    DenormModel = apps.get_model('denorm', 'DirtyInstance')
    distinct = DenormModel.objects.distinct('object_id', 'content_type')
    DenormModel.objects.exclude(id__in=distinct).delete()


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
        migrations.RunPython(drop_duplicates, reverse_code=migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='dirtyinstance',
            unique_together=set([('content_type', 'object_id')]),
        ),
    ]
