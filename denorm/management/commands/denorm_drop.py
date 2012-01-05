from django.core.management.base import NoArgsCommand
from optparse import make_option


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--using', dest='using', help='Select database connection'),
    )
    help = "Removes all triggers created by django-denorm."

    def handle_noargs(self, **options):
        from denorm import denorms
        using = options.get('using')
        denorms.drop_triggers(using=using)
