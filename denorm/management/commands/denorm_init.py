from django.core.management.base import BaseCommand
from optparse import make_option


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--using', dest='using', help='Select database connection'),
    )
    help_test = 'Creates all triggers needed by django-denorm'

    def handle(self, **kwargs):
        from denorm import denorms
        using = kwargs.get('using')
        denorms.install_triggers(using=using)
