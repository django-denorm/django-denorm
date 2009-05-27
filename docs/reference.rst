=========
Reference
=========


Decorators
==========

.. autofunction:: denorm.denormalized

.. autofunction:: denorm.depend_on_related(othermodel,foreign_key=None,type=None)

Functions
=========

.. autofunction:: denorm.flush

Settings
========

**DENORM_FLUSH_AFTER_REQUEST**
    If set, django-denorm will connect signal handler to ``django.core.signals.request_finished``
    that calls ``denorm.flush`` after every request. If your data mostly or only changes during requests
    this should be a good idea. If you run into performance problems with this (because ``flush()`` takes
    to long to complete) you can try using a daemon or handle flushing manually instead.


Management commands
===================

**denorm_init**
    .. automodule:: denorm.management.commands.denorm_init

**denorm_rebuild**
    .. automodule:: denorm.management.commands.denorm_rebuild

**denorm_flush**
    .. automodule:: denorm.management.commands.denorm_flush

**denorm_daemon**
    .. automodule:: denorm.management.commands.denorm_daemon
