from optparse import make_option
from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every denormalized field that was marked dirty, calculating only once " \
           "(content_type, object_id) values in each of chunk passes."

    def handle(self, **kwargs):
        denorms.flush_cached()
