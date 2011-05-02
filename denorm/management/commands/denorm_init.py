"""
Creates all triggers needed to track changes to models that may cause
data to become inconsistent.
"""
from django.core.management.base import BaseCommand

class Command(BaseCommand):

    def handle(self, **kwargs):
        from denorm import denorms
        using = kwargs.get('using')
        denorms.install_triggers(using=using)
