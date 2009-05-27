"""
Recalculates the value of every single denormalized model field in the whole project.
"""
from django.core.management.base import BaseCommand
from denorm import fields

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        fields.rebuildall()
