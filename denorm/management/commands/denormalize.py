from django.core.management.base import BaseCommand
from denorm import fields

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if args:
            if args[0] == "rebuild":
                fields.rebuildall()
                return
            if args[0] == "init":
                fields.install_triggers()
                return
            if args[0] == "flush":
                fields.flush()
                return

        print "unknown subcommand"
        print "subcommands are:"
        print "    rebuild"
        print "    init"
        print "    flush"
