from optparse import make_option
from datetime import datetime
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Benchmark provided function"
    option_list = BaseCommand.option_list + (
        make_option('-f',
            action='store',
            dest='function_name',
            default='denorm_flush',
            help=''),
    )

    def handle(self, **options):
        function_name = options.pop('function_name')

        start = datetime.now()
        print "Starting benchmark of `%s`: %s" % (function_name, start)

        call_command(function_name)
        end = datetime.now()

        print "Ending benchmark of `%s`: %s" % (function_name, end)
        print "Benchmark lasted: %s" % (end - start,)

