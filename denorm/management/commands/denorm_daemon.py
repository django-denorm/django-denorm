import os
import sys
import django
from time import sleep
from optparse import make_option

try:  # Django>=1.8
    from django.core.management.base import BaseCommand
except ImportError:
    from django.core.management.base import NoArgsCommand as BaseCommand
from django.db import transaction

from denorm import denorms

PID_FILE = "/tmp/django-denorm-daemon-pid"

if 'set_autocommit' in dir(transaction):
    def commit_manually(fn):  # replacement of transaction.commit_manually decorator removed in Django 1.6
        def _commit_manually(*args, **kwargs):
            transaction.set_autocommit(False)
            res = fn(*args, **kwargs)
            transaction.commit()
            transaction.set_autocommit(True)
            return res
        return _commit_manually
else:  # Django <= 1.5
    commit_manually = transaction.commit_manually


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-n',
            action='store_true',
            dest='foreground',
            default=False,
            help='Run in foreground',
        ),
        parser.add_argument(
            '-i',
            action='store',
            type=int,
            dest='interval',
            default=1,
            help='The interval - in seconds - between each update',
        ),
        parser.add_argument(
            '-f', '--pidfile',
            action='store',
            type=str,
            dest='pidfile',
            default=PID_FILE,
            help='The pid file to use. Defaults to "%s".' % PID_FILE),
        parser.add_argument(
            '-o',
            action='store_true',
            dest='run_once',
            default=False,
            help='Run only once (for testing purposes)',
        ),
    if django.VERSION < (1, 8):
        option_list = BaseCommand.option_list + (
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
                help='The pid file to use. Defaults to "%s".' % PID_FILE),
            make_option(
                '-o',
                action='store_true',
                dest='run_once',
                default=False,
                help='Run only once (for testing purposes)',
            ),
        )
    help = "Runs a daemon that checks for dirty fields and updates them in regular intervals."

    def pid_exists(self, pidfile):
        try:
            pid = int(open(pidfile, 'r').read())
            os.kill(pid, 0)
            self.stderr.write(self.style.ERROR("daemon already running as pid: %s\n" % (pid,)))
            return True
        except OSError as err:
            return err.errno == os.errno.EPERM
        except IOError as err:
            if err.errno == 2:
                return False
            else:
                raise

    @commit_manually
    def handle(self, **options):
        foreground = options['foreground']
        interval = options['interval']
        pidfile = options['pidfile']
        run_once = options['run_once']

        if self.pid_exists(pidfile):
            return

        if not foreground:
            from denorm import daemon
            daemon.daemonize(noClose=True, pidfile=pidfile)

        while not run_once:
            try:
                denorms.flush()
                sleep(interval)
                transaction.commit()
            except KeyboardInterrupt:
                transaction.commit()
                sys.exit()

    def handle_noargs(self, **options):  # Django<=1.8
        return self.handle(options)
