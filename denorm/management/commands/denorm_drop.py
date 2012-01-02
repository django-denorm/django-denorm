from django.core.management.base import BaseCommand
from optparse import make_option


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--using', dest='using', help='Select database connection'),
    )
    help = "Removes all triggers created by django-denorm."

    def handle(self, **kwargs):
        from denorm import denorms
        using = kwargs.get('using')
        denorms.drop_triggers(using=using)
