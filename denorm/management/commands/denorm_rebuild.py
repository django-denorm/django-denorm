"""
Recalculates the value of every single denormalized model field in the whole project.
"""
from django.core.management.base import BaseCommand
from denorm import denorms

class Command(BaseCommand):

    def handle(self, model_name=None, *args, **kwargs):
        denorms.rebuildall(model_name)
