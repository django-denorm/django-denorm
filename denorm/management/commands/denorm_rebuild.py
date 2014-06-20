from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every single denormalized model field in the whole project."

    def handle(self, model_name=None, *args, **kwargs):
        verbosity = int((kwargs.get('verbosity', 0)))
        denorms.rebuildall(verbose=verbosity > 1, model_name=model_name)
