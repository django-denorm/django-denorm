from django.core.management.base import BaseCommand
from denorm import fields

from django.db import transaction

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
            if args[0] == "daemon":
                self.daemon(args)

        print "unknown subcommand"
        print "subcommands are:"
        print "    rebuild"
        print "    init"
        print "    flush"
        print "    daemon"

    
    @transaction.commit_manually
    def daemon(self,args):
        from time import sleep
        from denorm import daemon
        daemon.daemonize(noClose=True)

        interval = int(args[1])
        while True:
            fields.flush()
            sleep(interval)
            transaction.commit()
