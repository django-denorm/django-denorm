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

Middleware
==========

.. autoclass:: denorm.middleware.DenormMiddleware


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

**denorm_sql**
    .. automodule:: denorm.management.commands.denorm_sql
