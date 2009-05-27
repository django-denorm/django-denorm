"""
Recalculates the value of every denormalized field that was marked dirty.
"""
from django.core.management.base import BaseCommand
from denorm import fields

class Command(BaseCommand):

    def handle(self, **kwargs):
        fields.flush()
