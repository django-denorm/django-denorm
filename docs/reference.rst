=========
Reference
=========


Decorators
==========

``@denormalized(FieldClass, *args, **kwargs)``
----------------------------------------------


``@depend_on_related(model, foreign_key=None, type=None)``
----------------------------------------------------------


Management commands
===================

``denorm_init``
---------------

Creates all triggers needed to track changes to models that may cause
data to become inconsistent.

``denorm_rebuild``
------------------

Recalculates the value of every single denormalized model field in the whole project.

``denorm_flush``
----------------

Recalculates the value of every denormalized field that was marked dirty.

``denorm_daemon``
-----------------

Runs a daemon that checks for dirty fields and updates them in regular intervals.
The default interval ist one second, this can be overridden by specifying the desired
interval as a numeric argument to the command.
