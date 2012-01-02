from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every single denormalized model field in the whole project."

    def handle(self, *args, **kwargs):
        denorms.rebuildall(verbose=True)
