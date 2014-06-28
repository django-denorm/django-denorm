from optparse import make_option
from decimal import Decimal

from django.db import transaction, connection
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from test_app.models import CachedModelA, CachedModelB
from denorm.models import DirtyInstance


class Command(BaseCommand):
    help = "Creates "
    option_list = BaseCommand.option_list + (
        make_option('-o',
            action='store',
            dest='objects_count',
            default='5000',
            help='How many objects do we prepare? default: 5000'),
        make_option('-p',
            action='store',
            dest='repeated_dirty_instances_percent',
            default='5',
            help='Percent of repeated DirtyInstances (for the same object), default: 5'),
    )

    @transaction.commit_manually
    def handle(self, **options):
        options['objects_count'] = int(options['objects_count'])
        options['repeated_dirty_instances_percent'] = int(options['repeated_dirty_instances_percent'])
        repeated_dirty_instances_count = int(
            Decimal(options['repeated_dirty_instances_percent']) / 100 * options['objects_count']
        )

        objects_db_count = CachedModelB.objects.count()

        # add CachedModelB
        b_list = (options['objects_count'] - objects_db_count) * [CachedModelB(data='I is a string!')]
        CachedModelB.objects.bulk_create(
            b_list
        )
        transaction.commit()
        del b_list

        # add CachedModelA connected with CachedModelB
        objects_db_count = CachedModelA.objects.count()
        a_list = []
        for cmb_id in CachedModelB.objects.values_list('id', flat=True)[:options['objects_count'] - objects_db_count]:
            a_list.append(CachedModelA(b=CachedModelB(id=cmb_id)))
        for it in range(0, len(a_list) / 100):
            CachedModelA.objects.bulk_create(
                a_list[it * 100:(it + 1) * 100]
            )
            if it % 10 == 0:
                transaction.commit()
        transaction.commit()
        del a_list

        # remove all dirty instances
        cursor = connection.cursor()
        cursor.execute("TRUNCATE TABLE denorm_dirtyinstance;")
        transaction.commit()

        # create unique dirty instances
        di_list = []
        ct = ContentType.objects.get(app_label="test_app", model="cachedmodela")
        for _id in CachedModelA.objects.values_list('id', flat=True)\
                .order_by('id')[:options['objects_count'] - repeated_dirty_instances_count].iterator():
            di_list.append(DirtyInstance(content_type=ct, object_id=_id))
        DirtyInstance.objects.bulk_create(
            di_list
        )
        transaction.commit()
        del di_list

        # create repeated dirty instances
        di_list = []
        for modelA in CachedModelA.objects.all().order_by('-id')[:repeated_dirty_instances_count].iterator():
            di_list += 10 * [DirtyInstance(content_object=modelA)]
        DirtyInstance.objects.bulk_create(
            di_list
        )
        transaction.commit()
        del di_list
