# -*- coding: utf-8 -*-
from denorm.helpers import find_fks, find_m2ms, remote_field_model
from django.db import models
from django.db.models.fields import related
from django.db import connections, connection
import denorm
from django.contrib import contenttypes
import six


class DenormDependency(object):

    """
    Base class for real dependency classes.
    """

    def get_triggers(self, using):
        """
        Must return a list of ``denorm.triggers.Trigger`` instances
        """
        return []

    def get_quote_name(self, using):
        if using:
            cconnection = connections[using]
        else:
            cconnection = connection
        return cconnection.ops.quote_name

    def setup(self, this_model):
        """
        Remembers the model this dependency was declared in.
        """
        self.this_model = this_model


class DependOnRelated(DenormDependency):
    def __init__(self, othermodel, foreign_key=None, type=None, skip=None):
        self.other_model = othermodel
        self.fk_name = foreign_key
        self.type = type
        self.skip = skip or ()

    def setup(self, this_model):
        super(DependOnRelated, self).setup(this_model)

        # FIXME: this should not be necessary
        if self.other_model == related.RECURSIVE_RELATIONSHIP_CONSTANT:
            self.other_model = self.this_model

        if isinstance(self.other_model, six.string_types):
            # if ``other_model`` is a string, it certainly is a lazy relation.
            related.add_lazy_relation(self.this_model, None, self.other_model, self.resolved_model)
        else:
            # otherwise it can be resolved directly
            self.resolved_model(None, self.other_model, None)

    def resolved_model(self, data, model, cls):
        """
        Does all the initialization that had to wait until we knew which
        model we depend on.
        """
        self.other_model = model

        # Create a list of all ForeignKeys and ManyToManyFields between both related models, in both directions
        candidates = [('forward', fk) for fk in find_fks(self.this_model, self.other_model, self.fk_name)]
        if self.other_model != self.this_model or self.type:
            candidates += [('backward', fk) for fk in find_fks(self.other_model, self.this_model, self.fk_name)]
        candidates += [('forward_m2m', fk) for fk in find_m2ms(self.this_model, self.other_model, self.fk_name)]
        if self.other_model != self.this_model or self.type:
            candidates += [('backward_m2m', fk) for fk in find_m2ms(self.other_model, self.this_model, self.fk_name)]

        # If a relation type was given (forward,backward,forward_m2m or backward_m2m),
        # filter out all relations that do not match this type.
        candidates = [x for x in candidates if not self.type or self.type == x[0]]

        if len(candidates) > 1:
            raise ValueError("%s has more than one ForeignKey or ManyToManyField to %s (or reverse); cannot auto-resolve. Candidates are: %s\n"\
                             "HINT: try to specify foreign_key on depend_on_related decorators."
                             % (self.this_model, self.other_model, candidates))
        if not candidates:
            raise ValueError("%s has no ForeignKeys or ManyToManyFields to %s (or reverse); cannot auto-resolve."
                             % (self.this_model, self.other_model))

        # Now the candidates list contains exactly one item, thats our winner.
        self.type, self.field = candidates[0]


class CacheKeyDependOnRelated(DependOnRelated):

    def get_triggers(self, using):
        from denorm.db import triggers
        qn = self.get_quote_name(using)

        if not self.type:
            # 'resolved_model' model never got called...
            raise ValueError("The model '%s' could not be resolved, it probably does not exist" % self.other_model)

        content_type = str(contenttypes.models.ContentType.objects.get_for_model(self.this_model).pk)

        if self.type == "forward":
            from denorm.db import triggers
            # With forward relations many instances of ``this_model``
            # may be related to one instance of ``other_model``
            action_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s = NEW.%s" % (
                    qn(self.field.get_attname_column()[1]),
                    qn(self.other_model._meta.pk.get_attname_column()[1]),
                ),
            )
            action_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s = OLD.%s" % (
                    qn(self.field.get_attname_column()[1]),
                    qn(self.other_model._meta.pk.get_attname_column()[1]),
                ),
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if self.type == "backward":
            # With backward relations a change in ``other_model`` can affect
            # only one or two instances of ``this_model``.
            # If the ``other_model`` instance changes the value its ForeignKey
            # pointing to ``this_model`` both the old and the new related instance
            # are affected, otherwise only the one it is pointing to is affected.
            action_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s = NEW.%s" % (
                    qn(self.this_model._meta.pk.get_attname_column()[1]),
                    qn(self.field.get_attname_column()[1]),
                ),
            )
            action_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s = OLD.%s" % (
                    qn(self.this_model._meta.pk.get_attname_column()[1]),
                    qn(self.field.get_attname_column()[1]),
                ),
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new, action_old], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if "m2m" in self.type:
            # The two directions of M2M relations only differ in the column
            # names used in the intermediate table.
            if isinstance(self.field, models.ManyToManyField):
                if "forward" in self.type:
                    column_name = self.field.m2m_column_name()
                    reverse_column_name = self.field.m2m_reverse_name()
                if "backward" in self.type:
                    column_name = self.field.m2m_reverse_name()
                    reverse_column_name = self.field.m2m_column_name()
            else:
                if "forward" in self.type:
                    column_name = self.field.object_id_field_name
                    reverse_column_name = self.field.remote_field.model._meta.pk.column
                if "backward" in self.type:
                    column_name = self.field.remote_field.model._meta.pk.column
                    reverse_column_name = self.field.object_id_field_name

            # The first part of a M2M dependency is exactly like a backward
            # ForeignKey dependency. ``this_model`` is backward FK related
            # to the intermediate table.
            action_m2m_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s = NEW.%s" % (
                    qn(self.this_model._meta.pk.get_attname_column()[1]),
                    qn(column_name),
                ),
            )
            action_m2m_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s = OLD.%s" % (
                    qn(self.this_model._meta.pk.get_attname_column()[1]),
                    qn(column_name),
                ),
            )

            trigger_list = [
                triggers.Trigger(self.field, "after", "update", [action_m2m_new, action_m2m_old], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "insert", [action_m2m_new], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "delete", [action_m2m_old], content_type, using, self.skip),
            ]

            if isinstance(self.field, models.ManyToManyField):
                # Additionally to the dependency on the intermediate table
                # ``this_model`` is dependant on updates to the ``other_model``-
                # There is no need to track insert or delete events here,
                # because a relation can only be created or deleted by
                # by modifying the intermediate table.
                #
                # Generic relations are excluded because they have the
                # same m2m_table and model table.
                sql, params = triggers.TriggerNestedSelect(
                    self.field.m2m_db_table(),
                    (column_name,),
                    **{reverse_column_name: 'NEW.%s' % qn(self.other_model._meta.pk.get_attname_column()[1])}
                ).sql()
                action_new = triggers.TriggerActionUpdate(
                    model=self.this_model,
                    columns=(self.fieldname,),
                    values=(triggers.RandomBigInt(),),
                    where=(self.this_model._meta.pk.get_attname_column()[1] + ' IN (' + sql + ')', params),
                )
                trigger_list.append(triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip))

            return trigger_list

        return []


class CallbackDependOnRelated(DependOnRelated):

    """
    A DenormDependency that handles callbacks depending on fields
    in other models that are related to the dependent model.

    Two models are considered related if there is a ForeignKey or ManyToManyField
    on either of them pointing to the other one.
    """

    def __init__(self, othermodel, foreign_key=None, type=None, skip=None):
        """
        Attaches a dependency to a callable, indicating the return value depends on
        fields in an other model that is related to the model the callable belongs to
        either through a ForeignKey in either direction or a ManyToManyField.

        **Arguments:**

        othermodel (required)
            Either a model class or a string naming a model class.

        foreign_key
            The name of the ForeignKey or ManyToManyField that creates the relation
            between the two models.
            Only necessary if there is more than one relationship between the two models.

        type
            One of 'forward', 'backward', 'forward_m2m' or 'backward_m2m'.
            If there are relations in both directions specify which one to use.

        skip
            Use this to specify what fields change on every save().
            These fields will not be checked and will not make a model dirty when they change, to prevent infinite loops.
        """
        super(CallbackDependOnRelated, self).__init__(othermodel, foreign_key, type, skip)

    def get_triggers(self, using):
        from denorm.db import triggers
        qn = self.get_quote_name(using)

        if not self.type:
            # 'resolved_model' model never got called...
            raise ValueError("The model '%s' could not be resolved, it probably does not exist" % self.other_model)

        content_type = str(contenttypes.models.ContentType.objects.get_for_model(self.this_model).pk)

        if self.type == "forward":
            # With forward relations many instances of ``this_model``
            # may be related to one instance of ``other_model``
            # so we need to do a nested select query in the trigger
            # to find them all.
            action_new = triggers.TriggerActionInsert(
                model=denorm.models.DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=triggers.TriggerNestedSelect(
                    self.this_model._meta.pk.model._meta.db_table,
                    (content_type,
                        self.this_model._meta.pk.get_attname_column()[1]),
                    **{self.field.get_attname_column()[1]: "NEW.%s" % qn(self.other_model._meta.pk.get_attname_column()[1])}
                )
            )
            action_old = triggers.TriggerActionInsert(
                model=denorm.models.DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=triggers.TriggerNestedSelect(
                    self.this_model._meta.pk.model._meta.db_table,
                    (content_type,
                        self.this_model._meta.pk.get_attname_column()[1]),
                    **{self.field.get_attname_column()[1]: "OLD.%s" % qn(self.other_model._meta.pk.get_attname_column()[1])}
                )
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if self.type == "backward":
            # With backward relations a change in ``other_model`` can affect
            # only one or two instances of ``this_model``.
            # If the ``other_model`` instance changes the value its ForeignKey
            # pointing to ``this_model`` both the old and the new related instance
            # are affected, otherwise only the one it is pointing to is affected.
            action_new = triggers.TriggerActionInsert(
                model=denorm.models.DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=triggers.TriggerNestedSelect(
                    self.field.model._meta.db_table,
                    (content_type,
                        self.field.get_attname_column()[1]),
                    **{self.field.model._meta.pk.get_attname_column()[1]: "NEW.%s" % qn(self.other_model._meta.pk.get_attname_column()[1])}
                )
            )
            action_old = triggers.TriggerActionInsert(
                model=denorm.models.DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "OLD.%s" % self.field.get_attname_column()[1],
                ),
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new, action_old], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if "m2m" in self.type:
            # The two directions of M2M relations only differ in the column
            # names used in the intermediate table.
            if isinstance(self.field, models.ManyToManyField):
                if "forward" in self.type:
                    column_name = qn(self.field.m2m_column_name())
                    reverse_column_name = self.field.m2m_reverse_name()
                if "backward" in self.type:
                    column_name = qn(self.field.m2m_reverse_name())
                    reverse_column_name = self.field.m2m_column_name()
            else:
                if "forward" in self.type:
                    column_name = qn(self.field.object_id_field_name)
                    reverse_column_name = remote_field_model(self.field)._meta.pk.column
                if "backward" in self.type:
                    column_name = qn(remote_field_model(self.field)._meta.pk.column)
                    reverse_column_name = self.field.object_id_field_name

            # The first part of a M2M dependency is exactly like a backward
            # ForeignKey dependency. ``this_model`` is backward FK related
            # to the intermediate table.
            action_m2m_new = triggers.TriggerActionInsert(
                model=denorm.models.DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "NEW.%s" % column_name,
                )
            )
            action_m2m_old = triggers.TriggerActionInsert(
                model=denorm.models.DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "OLD.%s" % column_name,
                )
            )

            trigger_list = [
                triggers.Trigger(self.field, "after", "update", [action_m2m_new, action_m2m_old], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "insert", [action_m2m_new], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "delete", [action_m2m_old], content_type, using, self.skip),
            ]

            if isinstance(self.field, models.ManyToManyField):
                # Additionally to the dependency on the intermediate table
                # ``this_model`` is dependant on updates to the ``other_model``-
                # There is no need to track insert or delete events here,
                # because a relation can only be created or deleted by
                # by modifying the intermediate table.
                #
                # Generic relations are excluded because they have the
                # same m2m_table and model table.
                action_new = triggers.TriggerActionInsert(
                    model=denorm.models.DirtyInstance,
                    columns=("content_type_id", "object_id"),
                    values=triggers.TriggerNestedSelect(
                        self.field.m2m_db_table(),
                        (content_type, column_name),
                        **{reverse_column_name: 'NEW.%s' % qn(self.other_model._meta.pk.get_attname_column()[1])}
                    )
                )
                trigger_list.append(triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip))

            return trigger_list

        return []


def make_depend_decorator(Class):
    """
    Create a decorator that attaches an instance of the given class
    to the decorated function, passing all remaining arguments to the classes
    __init__.
    """
    import functools

    def decorator(*args, **kwargs):
        def deco(func):
            if not hasattr(func, 'depend'):
                func.depend = []
            func.depend.append((Class, args, kwargs))
            return func
        return deco
    functools.update_wrapper(decorator, Class.__init__)
    return decorator

depend_on_related = make_depend_decorator(CallbackDependOnRelated)
