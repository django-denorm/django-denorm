from django.core.management.base import NoArgsCommand
from optparse import make_option
from denorm import denorms


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--using', dest='using', help='Select database connection'),
    )
    help = "Creates all triggers needed by django-denorm."

    def handle_noargs(self, **options):
        using = options.get('using')
        denorms.install_triggers(using=using)
