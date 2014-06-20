import os
import sys
from time import sleep
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.db import transaction

from denorm import denorms

PID_FILE = "/tmp/django-denorm-daemon-pid"


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option(
            '-n',
            action='store_true',
            dest='foreground',
            default=False,
            help='Run in foreground',
        ),
        make_option(
            '-i',
            action='store',
            type='int',
            dest='interval',
            default=1,
            help='The interval - in seconds - between each update',
        ),
        make_option(
            '-f', '--pidfile',
            action='store',
            type='string',
            dest='pidfile',
            default=PID_FILE,
            help='The pid file to use. Defaults to "%s".' % PID_FILE)
    )
    help = "Runs a daemon that checks for dirty fields and updates them in regular intervals."

    def pid_exists(self, pidfile):
        try:
            pid = int(file(pidfile, 'r').read())
            os.kill(pid, 0)
            self.stderr.write(self.style.ERROR("daemon already running as pid: %s\n" % (pid,)))
            return True
        except OSError, err:
            return err.errno == os.errno.EPERM
        except IOError, err:
            if err.errno == 2:
                return False
            else:
                raise

    @transaction.commit_manually
    def handle_noargs(self, **options):
        foreground = options['foreground']
        interval = options['interval']
        pidfile = options['pidfile']

        if self.pid_exists(pidfile):
            return

        if not foreground:
            from denorm import daemon
            daemon.daemonize(noClose=True, pidfile=pidfile)

        while True:
            try:
                denorms.flush()
                sleep(interval)
                transaction.commit()
            except KeyboardInterrupt:
                transaction.commit()
                sys.exit()
