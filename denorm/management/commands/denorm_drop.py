"""
Removes all triggers created by denorm.
"""
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, **kwargs):
        from denorm import denorms
        using = kwargs.get('using')
        denorms.drop_triggers(using=using)
