from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every denormalized field that was marked dirty."

    def handle(self, **kwargs):
        denorms.flush()
