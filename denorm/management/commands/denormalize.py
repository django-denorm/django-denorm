from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):

    def handle(self, **options):
        raise CommandError("This management command is deprecated. "
            "Please consult the documentation for a command reference.")
