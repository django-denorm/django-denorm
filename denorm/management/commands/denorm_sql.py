from django.core.management.base import NoArgsCommand
from denorm import denorms


class Command(NoArgsCommand):
    help = "Prints out the SQL used to create all triggers needed to track changes to models that may cause data to become inconsistent."

    def handle_noargs(self, **options):
        triggerset = denorms.build_triggerset()
        print u'\n'.join((trigger.sql() for name, trigger in triggerset.triggers.iteritems()))
