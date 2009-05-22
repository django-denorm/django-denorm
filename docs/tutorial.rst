Tutorial
========

Creating denormalized fields
----------------------------

A denormalized field can be created from a python function by using the ``denormalized`` decorator.
The decorator takes at least one argument: the database field type you want to use to store the computed
value. Any additional arguments will be passed into the constructor of the specified field when it is actually
created.

If you already use the ``@property`` decorator that comes with python to make your computed values accessible
like attributes, you can just replace ``@property`` with ``@denormalized(..)`` and you probably won't need
to change any code outside your model.

Now whenever an instance of your model gets saved, the value stored in the field will get updated
with whatever value the decorated function returns.

Example::

    class SomeModel(models.Model):
        # the other fields
        @denormalized(models.CharField,max_length=100)
        def some_computation(self):
           # your code
           return some_value

in this example ``SomeModel`` will get a ``CharField`` named ``some_computation``.


Adding dependency information
-----------------------------

The above example will only work correctly if the return value of the
decorated function only depends on attributes of the same instance of the same
model it belongs to.

If the value somehow depends on information stored in other models, it will get
out of sync as those external information changes.

As this is a very undesirable effect, django-denorm provides a mechanism to
tell it what other model instances will effect the computed value. It provides
additional decorators to attach this dependency information to the function
before it gets turned into a field.

Simple dependencies
'''''''''''''''''''


In most cases your model probably contains a ForeignKey to some other model
(forward foreign key relationship) or an other model has a ForeignKey to the
model containing the denormalized field (backward foreign key relationship),
and your function will somehow use the information in the related instance to
compute its return value.

This kind of dependency can be expressed like this::

    class SomeModel(models.Model):
        # the other fields
        other = models.ForeignKey('SomeOtherModel')

        @denormalized(models.CharField,max_length=100)
        @depend_on_related('SomeOtherModel')
        def some_computation(self):
           # your code
           return some_value

The ``depend_on_related`` decorator takes the related model as an argument in
the same was ``ForeignKey`` does, so you can use the same conventions here.
``depend_on_related`` will then detect what kind (forward/backward) of relationship the two
models have and update the value whenever the related instance of the other
model changes.

In case of an ambiguous relationship (maybe there are multiple foreign keys
to the related model) an error will be raised, and you'll need to specify the
name of the ForeignKey to use as a second argument like this::

    ...
        @depend_on_related('SomeOtherModel','other')
    ...

