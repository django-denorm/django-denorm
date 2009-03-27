from django.core.management.base import BaseCommand
from denorm import fields

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        fields.install_triggers()
