from django.core.management.base import BaseCommand
from optparse import make_option
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every single denormalized model field in the whole project."
    option_list = BaseCommand.option_list + (
        make_option('--paginate_by',
                    dest='paginate_by',
                    type='int',
                    help='chose the chunk size to use'),
    )

    def handle(self, model_name=None, paginate_by=None, *args, **kwargs):
        verbosity = int((kwargs.get('verbosity', 0)))
        denorms.rebuildall(verbose=verbosity > 1,
                           model_name=model_name,
                           paginate_by=paginate_by)
