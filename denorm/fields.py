# -*- coding: utf-8 -*-
from django.db import models, connection
from . import denorms
from django.conf import settings
import django.db.models


def denormalized(DBField, *args, **kwargs):
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

        def __init__(self, func=None, *args, **kwargs):
            self.func = func
            self.skip = kwargs.pop('skip', None)
            kwargs['editable'] = False
            DBField.__init__(self, *args, **kwargs)

        def contribute_to_class(self, cls, name, *args, **kwargs):
            if hasattr(settings, 'DENORM_BULK_UNSAFE_TRIGGERS') and settings.DENORM_BULK_UNSAFE_TRIGGERS:
                self.denorm = denorms.BaseCallbackDenorm(skip=self.skip)
            else:
                self.denorm = denorms.CallbackDenorm(skip=self.skip)
            self.denorm.func = self.func
            self.denorm.depend = [dcls(*dargs, **dkwargs) for (dcls, dargs, dkwargs) in getattr(self.func, 'depend', [])]
            self.denorm.model = cls
            self.denorm.fieldname = name
            self.field_args = (args, kwargs)
            models.signals.class_prepared.connect(self.denorm.setup, sender=cls)
            # Add The many to many signal for this class
            models.signals.pre_save.connect(denorms.many_to_many_pre_save, sender=cls)
            models.signals.post_save.connect(denorms.many_to_many_post_save, sender=cls)
            DBField.contribute_to_class(self, cls, name, *args, **kwargs)

        def pre_save(self, model_instance, add):
            """
            Updates the value of the denormalized field before it gets saved.
            """
            value = self.denorm.func(model_instance)

            if hasattr(self, "remote_field") and self.remote_field:  # Django>=1.10
                related_field_model = self.remote_field.model
            elif hasattr(self, 'related_field'):  # Django>1.5
                related_field_model = self.related_field.model
            elif hasattr(self, "related"):
                try:
                    related_field_model = self.related.parent_model
                except AttributeError:
                    related_field_model = self.related.model
            else:
                related_field_model = None

            if related_field_model and isinstance(value, related_field_model):
                setattr(model_instance, self.attname, None)
                setattr(model_instance, self.name, value)
                return getattr(model_instance, self.attname)
            else:
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

        def deconstruct(self):
            name, path, args, kwargs = super(DenormDBField, self).deconstruct()
            super_name, super_path, super_args, super_kwargs = DBField(*args, **kwargs).deconstruct()
            return name, super_path, args, kwargs

    def deco(func):
        dbfield = DenormDBField(func, *args, **kwargs)
        return dbfield
    return deco


class AggregateField(models.PositiveIntegerField):

    def get_denorm(self, *args, **kwargs):
        """
        Returns denorm instance
        """
        raise NotImplemented('You need to override this method')

    def __init__(self, manager_name=None, **kwargs):
        """
        **Arguments:**

        manager_name:
            The name of the related manager to be counted.

        filter:
            Filter, which is applied to manager. For example:

        >>> active_item_count = CountField('item_set', filter={'active__exact':True})
        >>> adult_user_count = CountField('user_set', filter={'age__gt':18})

        exclude:
            Do not include filter in aggregation

        Any additional arguments are passed on to the contructor of
        PositiveIntegerField.
        """
        skip = kwargs.pop('skip', None)
        qs_filter = kwargs.pop('filter', {})
        if qs_filter and connection.vendor == "sqlite":
            raise NotImplementedError('filters for aggregate fields are currently not supported for sqlite')
        qs_exclude = kwargs.pop('exclude', {})
        self.denorm = self.get_denorm(skip)
        self.denorm.manager_name = manager_name
        self.denorm.filter = qs_filter
        self.denorm.exclude = qs_exclude
        self.kwargs = kwargs
        kwargs['default'] = 0
        kwargs['editable'] = False
        super(AggregateField, self).__init__(**kwargs)

    def contribute_to_class(self, cls, name, *args, **kwargs):
        self.denorm.model = cls
        self.denorm.fieldname = name
        models.signals.class_prepared.connect(self.denorm.setup)
        super(AggregateField, self).contribute_to_class(cls, name, *args, **kwargs)

    def south_field_triple(self):
        return (
            '.'.join(('django', 'db', 'models', models.PositiveIntegerField.__name__)),
            [],
            {
                'default': '0',
            },
        )

    def pre_save(self, model_instance, add):
        """
        Makes sure we never overwrite the count with an outdated value.
        This is necessary because if the count was changed by
        a trigger after this model instance was created, the value
        we would write has not been updated.
        """
        if add:
            # if this is a new instance there can't be any related objects yet
            value = 0
        else:
            # if we're updating, get the most recent value from the DB
            try:
                value = self.denorm.model.objects.filter(
                    pk=model_instance.pk,
                ).values_list(
                    self.attname, flat=True,
                )[0]
            except IndexError:
                # Aggregate fields on models that inherit from another concrete model
                # call pre_save with add=False even when first saved in Django 1.6+
                value = 0

        setattr(model_instance, self.attname, value)
        return value

    def deconstruct(self):
        name, path, args, kwargs = super(AggregateField, self).deconstruct()
        del kwargs['editable']
        args = [self.denorm.manager_name] + args
        return name, path, args, kwargs


class CountField(AggregateField):
    """
    A ``PositiveIntegerField`` that stores the number of rows
    related to this model instance through the specified manager.
    The value will be incrementally updated when related objects
    are added and removed.

    """

    def __init__(self, manager_name=None, **kwargs):
        """
        **Arguments:**

        manager_name:
            The name of the related manager to be counted.

        filter:
            Filter, which is applied to manager. For example:

        >>> active_item_count = CountField('item_set', filter={'active__exact':True})
        >>> adult_user_count = CountField('user_set', filter={'age__gt':18})

        Any additional arguments are passed on to the contructor of
        PositiveIntegerField.
        """

        kwargs['editable'] = False
        super(CountField, self).__init__(manager_name, **kwargs)

    def get_denorm(self, skip):
        return denorms.CountDenorm(skip)


class SumField(AggregateField):
    """
    A ``PositiveIntegerField`` that stores sub of related field values
    to this model instance through the specified manager.
    The value will be incrementally updated when related objects
    are added and removed.

    """

    def __init__(self, manager_name=None, field=None, **kwargs):
        self.field = field
        kwargs['editable'] = False
        super(SumField, self).__init__(manager_name, **kwargs)

    def get_denorm(self, skip):
        return denorms.SumDenorm(skip, self.field)


class CopyField(AggregateField):
    """
    Field, which makes two field identical. Any change in related field will change this field
    """
    # TODO: JFDI


class CacheKeyField(models.BigIntegerField):
    """
    A ``BigIntegerField`` that gets set to a random value anytime
    the model is saved or a dependency is triggered.
    The field gets updated immediately and does not require *denorm.flush()*.
    It currently cannot detect a direct (bulk)update to the model
    it is declared in.
    """

    def __init__(self, **kwargs):
        """
        All arguments are passed on to the contructor of
        BigIntegerField.
        """
        self.dependencies = []
        kwargs['default'] = 0
        kwargs['editable'] = False
        self.kwargs = kwargs
        super(CacheKeyField, self).__init__(**kwargs)

    def depend_on_related(self, *args, **kwargs):
        """
        Add dependency information to the CacheKeyField.
        Accepts the same arguments like the *denorm.depend_on_related* decorator
        """
        from .dependencies import CacheKeyDependOnRelated
        self.dependencies.append(CacheKeyDependOnRelated(*args, **kwargs))

    def contribute_to_class(self, cls, name, *args, **kwargs):
        for depend in self.dependencies:
            depend.fieldname = name
        self.denorm = denorms.BaseCacheKeyDenorm(depend_on_related=self.dependencies)
        self.denorm.model = cls
        self.denorm.fieldname = name
        models.signals.class_prepared.connect(self.denorm.setup)
        super(CacheKeyField, self).contribute_to_class(cls, name, *args, **kwargs)

    def pre_save(self, model_instance, add):
        if add:
            value = self.denorm.func(model_instance)
        else:
            value = self.denorm.model.objects.filter(
                pk=model_instance.pk,
            ).values_list(
                self.attname, flat=True,
            )[0]
        setattr(model_instance, self.attname, value)
        return value

    def south_field_triple(self):
        return (
            '.'.join(('django', 'db', 'models', models.BigIntegerField.__name__)),
            [],
            {
                'default': '0',
            },
        )


class CacheWrapper(object):
    def __init__(self, field):
        self.field = field

    def __set__(self, obj, value):
        key = 'CachedField_%s' % value
        cached = self.field.cache.get(key)
        if not cached:
            cached = self.field.func(obj)
            self.field.cache.set(key, cached, 60 * 60 * 24 * 30)
        obj.__dict__[self.field.name] = cached


class CachedField(CacheKeyField):
    def __init__(self, func=None, cache=None, *args, **kwargs):
        self.func = func
        self.cache = cache
        super(CachedField, self).__init__(*args, **kwargs)
        if func and cache:
            for c, a, kw in self.func.depend:
                self.depend_on_related(*a, **kw)

    def contribute_to_class(self, cls, name, *args, **kwargs):
        super(CachedField, self).contribute_to_class(cls, name, *args, **kwargs)
        setattr(cls, self.name, CacheWrapper(self))


def cached(cache, *args, **kwargs):
    def deco(func):
        dbfield = CachedField(func, cache, *args, **kwargs)
        return dbfield
    return deco
