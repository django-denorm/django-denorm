from django.core.management.base import BaseCommand
from denorm import fields

from django.db import transaction

class Command(BaseCommand):
    pidfile = "/tmp/django-denorm-daemon-pid"

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

            else:
                print "unknown subcommand"
                print "subcommands are:"
                print "    rebuild"
                print "    init"
                print "    flush"
                print "    daemon"

    def pid_exists(self):
        import os
        try:
            pid = int(file(self.pidfile,"r").read())
            os.kill(pid, 0)
            print "daemon alreay running as pid: %s" % (pid,)
            return 1
        except OSError, err:
            return err.errno == os.errno.EPERM
        except IOError, err:
            if err.errno == 2:
                return False
            else:
                raise


    
    @transaction.commit_manually
    def daemon(self,args):
        if self.pid_exists():
            return
        from time import sleep
        from denorm import daemon
        pid = daemon.daemonize(noClose=True,pidfile=self.pidfile)

        interval = int(args[1])
        while True:
            fields.flush()
            sleep(interval)
            transaction.commit()
