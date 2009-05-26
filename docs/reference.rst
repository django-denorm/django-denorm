=========
Reference
=========


Decorators
==========

``@denormalized (FieldClass, *args, **kwargs)``
-----------------------------------------------

Turns a callable into model field, analogous to python's ``@property`` decorator.
The callable will be used to compute the value of the field every time the model
gets saved.
If the callable has dependency information attached to it the fields value will
also be recomputed if the dependencies require it.

**Arguments:**

FieldClass (required)
    The type of field you want to use to save the data.
    Note that you have to use the field class and not an instance
    of it.

\*args, \*\*kwargs:
    Those will be passed unaltered into the constructor of ``FieldClass``
    once it gets actually created.


``@depend_on_related (othermodel, foreign_key=None, type=None)``
----------------------------------------------------------------

Attaches a dependency to a callable, indicating the return value depends on
fields in an other model that is related to the model the callable belongs to
either through a ForeignKey in either direction or a ManyToManyField.

**Arguments:**

othermodel (required)
    Either a model class or a string naming a model class.

foreign_key
    The name of the ForeignKey or ManyToManyField that creates the relation
    between the two models.
    This is needed to specify witch one to use in case there are more than one.

type
    One of 'forward', 'backward', 'forward_m2m' or 'backward_m2m'.
    If there are relations in both directions specify witch one to use.

Settings
========

DENORM_FLUSH_AFTER_REQUEST
--------------------------

If set, django-denorm will connect signal handler to ``django.core.signals.request_finished``
that calls ``denorm.flush`` after every request. If your data mostly or only changes during requests
this should be a good idea. If you run into performance problems with this (because ``flush()`` takes
to long to complete) you can try using a daemon or handle flushing manually instead.


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
