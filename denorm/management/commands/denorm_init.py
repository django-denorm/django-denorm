"""
Creates all triggers needed to track changes to models that may cause
data to become inconsistent.
"""
from django.core.management.base import BaseCommand
from denorm import denorms

class Command(BaseCommand):

    def handle(self, **kwargs):
        denorms.install_triggers()
