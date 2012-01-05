from django.core.management.base import NoArgsCommand
from denorm import denorms


class Command(NoArgsCommand):
    help = "Recalculates the value of every single denormalized model field in the whole project."

    def handle_noargs(self, **options):
        denorms.rebuildall(verbose=True)
