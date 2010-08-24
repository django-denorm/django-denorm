# -*- coding: utf-8 -*-
from django.db import models
from denorm import denorms
from django.conf import settings

def denormalized(DBField,*args,**kwargs):
    """
    Turns a callable into model field, analogous to python's ``@property`` decorator.
    The callable will be used to compute the value of the field every time the model
    gets saved.
    If the callable has dependency information attached to it the fields value will
    also be recomputed if the dependencies require it.

    **Arguments:**

    DBField (required)
        The type of field you want to use to save the data.
        Note that you have to use the field class and not an instance
        of it.

    \*args, \*\*kwargs:
        Those will be passed unaltered into the constructor of ``DBField``
        once it gets actually created.
    """

    class DenormDBField(DBField):

        """
        Special subclass of the given DBField type, with a few extra additions.
        """

        def contribute_to_class(self,cls,name,*args,**kwargs):
            self.denorm.model = cls
            self.denorm.fieldname = name
            self.field_args = (args, kwargs)
            models.signals.class_prepared.connect(self.denorm.setup,sender=cls)
            # Add The many to many signal for this class
            models.signals.pre_save.connect(denorms.many_to_many_pre_save,sender=cls)
            models.signals.post_save.connect(denorms.many_to_many_post_save,sender=cls)
            DBField.contribute_to_class(self,cls,name,*args,**kwargs)

        def pre_save(self,model_instance,add):
            """
            Updates the value of the denormalized field before it gets saved.
            """
            value = self.denorm.func(model_instance)
            setattr(model_instance, self.attname, value)
            return value

        def south_field_triple(self):
            """
            Because this field will be defined as a decorator, give
            South hints on how to recreate it for database use.
            """
            from south.modelsinspector import introspector
            field_class = DBField.__module__ + "." + DBField.__name__
            args, kwargs = introspector(self)
            return (field_class, args, kwargs)

    def deco(func):
        if hasattr(settings, 'DENORM_BULK_UNSAFE_TRIGGERS') and settings.DENORM_BULK_UNSAFE_TRIGGERS:
            denorm = denorms.BaseCallbackDenorm()
        else:
            denorm = denorms.CallbackDenorm()
        denorm.func = func
        kwargs["blank"] = True
        kwargs["null"] = True
        dbfield = DenormDBField(*args,**kwargs)
        dbfield.denorm = denorm
        return dbfield
    return deco

class CountField(models.PositiveIntegerField):
    """
    A ``PositiveIntegerField`` that stores the number of rows
    related to this model instance through the specified manager.
    The value will be incrementally updated when related objects
    are added and removed.

    **Arguments:**

    manager_name:
        The name of the related manager to be counted.

    Any additional arguments are passed on to the contructor of
    PositiveIntegerField.
    """
    def __init__(self,manager_name,**kwargs):
        self.denorm = denorms.CountDenorm()
        self.denorm.manager_name = manager_name
        self.kwargs = kwargs
        kwargs['default'] = 0
        super(CountField,self).__init__(**kwargs)

    def contribute_to_class(self,cls,name,*args,**kwargs):
        self.denorm.model = cls
        self.denorm.fieldname = name
        models.signals.class_prepared.connect(self.denorm.setup)
        super(CountField,self).contribute_to_class(cls,name,*args,**kwargs)

    def south_field_triple(self):
        return (
            '.'.join(('django','db','models',models.PositiveIntegerField.__name__)),
            [],
            self.kwargs,
        )

    def pre_save(self,model_instance,add):
        """
        Makes sure we never overwrite the count with an
        outdated value.
        This is necessary because if the count was changed by
        a trigger after this model instance was created the value
        we would write has not been updated.
        """
        if add:
            # if this is a new instance there can't be any related objects yet
            value = 0
        else:
            # if we're updating, get the most recent value from the DB
            value = self.denorm.model.objects.filter(
                pk=model_instance.pk,
            ).values_list(
                self.attname,flat=True,
            )[0]

        setattr(model_instance, self.attname, value)
        return value
