from optparse import make_option

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
import django

from denorm import denorms


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to execute '
                'SQL into. Defaults to the "default" database.'
        ),

    help = "Removes all triggers created by django-denorm."

    def handle(self, **options):
        using = options['database']
        denorms.drop_triggers(using=using)
