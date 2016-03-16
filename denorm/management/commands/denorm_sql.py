from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Prints out the SQL used to create all triggers needed to track changes to models that may cause data to become inconsistent."

    def handle(self, **options):
        triggerset = denorms.build_triggerset()
        sql_list = []
        for name, trigger in triggerset.triggers.items():
            sql, params = trigger.sql()
            sql_list.append(sql % tuple(params))
        print('\n'.join(sql_list))
