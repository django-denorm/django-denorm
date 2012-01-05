from django.core.management.base import NoArgsCommand, CommandError


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        raise CommandError("This management command is deprecated. "
            "Please consult the documentation for a command reference.")
