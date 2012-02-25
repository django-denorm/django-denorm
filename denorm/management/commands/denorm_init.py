from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.db import DEFAULT_DB_ALIAS

from denorm import denorms


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to execute '
                'SQL into. Defaults to the "default" database.'),
    )
    help = "Creates all triggers needed by django-denorm."

    def handle_noargs(self, **options):
        using = options['database']
        denorms.install_triggers(using=using)
