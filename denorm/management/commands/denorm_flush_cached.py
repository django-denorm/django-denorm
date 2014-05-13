from optparse import make_option
from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every denormalized field that was marked dirty, calculating only once " \
           "(content_type, object_id) values in each of chunk passes."
    option_list = BaseCommand.option_list + (
        make_option('-c', '--chunk',
            action='store',
            dest='chunk',
            default='0',
            help='limit dirty object instances selected in one pass, 0=all'),
    )

    def handle(self, **kwargs):
        denorms.flush_cached(int(**kwargs['chunk']))
