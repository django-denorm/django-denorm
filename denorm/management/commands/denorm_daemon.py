from django.core.management.base import BaseCommand
from denorm import denorms

from django.db import transaction
from optparse import make_option


class Command(BaseCommand):
    pidfile = "/tmp/django-denorm-daemon-pid"

    option_list = BaseCommand.option_list + (
        make_option('-n',
            action='store_true',
            dest='foreground',
            default=False,
            help='run in foreground',
        ),
    )
    help = "Runs a daemon that checks for dirty fields and updates them in regular intervals." \
        "The default interval is one second, this can be overridden by specifying the desired" \
        "interval as a numeric argument to the command."

    def pid_exists(self):
        import os
        try:
            pid = int(file(self.pidfile, "r").read())
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
    def handle(self, interval=1, foreground=False, **kwargs):
        print interval
        if self.pid_exists():
            return
        from time import sleep

        if not foreground:
            from denorm import daemon
            pid = daemon.daemonize(noClose=True, pidfile=self.pidfile)

        interval = int(interval)
        while True:
            denorms.flush()
            sleep(interval)
            transaction.commit()
