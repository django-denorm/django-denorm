# -*- coding: utf-8 -*-
from denorm.helpers import find_fks, find_m2ms
from django.db import models
from django.db.models.fields import related
from denorm.models import DirtyInstance
from django.contrib.contenttypes.models import ContentType
from denorm.db import triggers


class DenormDependency(object):

    """
    Base class for real dependency classes.
    """

    def get_triggers(self, using):
        """
        Must return a list of ``denorm.triggers.Trigger`` instances
        """
        return []

    def setup(self, this_model):
        """
        Remembers the model this dependency was declared in.
        """
        self.this_model = this_model


class DependOnField(DenormDependency):
    def __init__(self, field_lookup):
        super(DependOnField, self).__init__()
        self.field_lookup = field_lookup

    def setup(self, this_model):
        super(DependOnField, self).setup(this_model)

        field_names = self.field_lookup.split('__')
        if len(field_names) > 2:
            raise ValueError("%s field lookup spans more than one relationship." % self.field_lookup)

        (self.field, _, direct, m2m) = this_model._meta.get_field_by_name(field_names[0])
        if m2m:
            if direct:
                self.type = "m2m forward"
                self.other_model = self.field.rel.to
            else:
                self.type = "m2m backward"
                self.other_model = self.field.model
        else:
            if direct:
                if isinstance(self.field.rel, related.ManyToOneRel):
                    self.type = "forward"
                    self.other_model = self.field.rel.to
                else:
                    self.type = ''
            else:
                self.type = "backward"
                self.other_model = self.field.model
                self.field = self.field.field

        if self.type == '' and len(field_names) > 1:
            raise ValueError("%s field lookup invalid." % self.field_lookup)
        if len(field_names) == 2:
            self.other_field = field_names[1]
        else:
            self.other_field = None


class CacheKeyDependOnField(DependOnField):

    def get_triggers(self, using):

        trigger_list = []

        content_type = str(ContentType.objects.get_for_model(self.this_model).id)

        if "m2m" not in self.type and self.type != "backward":
            action = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=NEW.%s" % ((self.this_model._meta.pk.get_attname_column()[1],) * 2),
            )
            trigger_list = [
                triggers.Trigger(self.this_model, "after", "update", [action], content_type, using, [self.field.attname]),
                triggers.Trigger(self.this_model, "after", "insert", [action], content_type, using),
            ]

        if self.type == "forward":
            # With forward relations many instances of ``this_model``
            # may be related to one instance of ``other_model``
            action_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=NEW.%s" % (
                    self.field.get_attname_column()[1],
                    self.other_model._meta.pk.get_attname_column()[1],
                ),
            )
            action_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=OLD.%s" % (
                    self.field.get_attname_column()[1],
                    self.other_model._meta.pk.get_attname_column()[1],
                ),
            )
            trigger_list = [
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using),
            ]
            if self.other_field:
                trigger_list.append(triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, [self.other_field]))

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
                where="%s=NEW.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    self.field.get_attname_column()[1],
                ),
            )
            action_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=OLD.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    self.field.get_attname_column()[1],
                ),
            )
            trigger_list = [
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using),
            ]
            if self.other_field:
                trigger_list.append(triggers.Trigger(self.other_model, "after", "update", [action_new, action_old], content_type, using, [self.other_field]))

        if "m2m" in self.type:
            # The two directions of M2M relations only differ in the column
            # names used in the intermediate table.
            if "forward" in self.type:
                column_name = self.field.m2m_column_name()
                reverse_column_name = self.field.m2m_reverse_name()
            if "backward" in self.type:
                column_name = self.field.m2m_reverse_name()
                reverse_column_name = self.field.m2m_column_name()

            # The first part of a M2M dependency is exactly like a backward
            # ForeignKey dependency. ``this_model`` is backward FK related
            # to the intermediate table.
            action_m2m_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=NEW.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    column_name,
                ),
            )
            action_m2m_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=OLD.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    column_name,
                ),
            )

            trigger_list = [
                triggers.Trigger(self.field, "after", "update", [action_m2m_new, action_m2m_old], content_type, using),
                triggers.Trigger(self.field, "after", "insert", [action_m2m_new], content_type, using),
                triggers.Trigger(self.field, "after", "delete", [action_m2m_old], content_type, using),
            ]

            if isinstance(self.field, models.ManyToManyField) and self.other_field:
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
                    **{reverse_column_name: "NEW.id"}
                ).sql()
                action_new = triggers.TriggerActionUpdate(
                    model=self.this_model,
                    columns=(self.fieldname,),
                    values=(triggers.RandomBigInt(),),
                    where=(self.this_model._meta.pk.get_attname_column()[1] + ' IN (' + sql + ')', params),
                )
                trigger_list.append(triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, [self.other_field]))

        return trigger_list


class CallbackDependOnField(DependOnField):
    def get_triggers(self, using):

        trigger_list = []

        content_type = str(ContentType.objects.get_for_model(self.this_model).id)

        if "m2m" not in self.type and self.type != "backward":
            # Create a trigger that marks any updated or newly created
            # instance of the model containing the denormalized field
            # as dirty.
            # This is only really needed if the instance was changed without
            # using the ORM or if it was part of a bulk update.
            # In those cases the self_save_handler won't get called by the
            # pre_save signal, so we need to ensure flush() does this later.
            action = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(content_type, "NEW.%s" % self.this_model._meta.pk.get_attname_column()[1])
            )
            trigger_list = [
                triggers.Trigger(self.this_model, "after", "update", [action], content_type, using, [self.field.attname]),
                triggers.Trigger(self.this_model, "after", "insert", [action], content_type, using),
            ]

        if self.type == "forward":
            # With forward relations many instances of ``this_model``
            # may be related to one instance of ``other_model``
            # so we need to do a nested select query in the trigger
            # to find them all.
            action_new = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,
                     self.this_model._meta.pk.get_attname_column()[1]),
                    **{self.field.get_attname_column()[1]: "NEW.%s" % self.other_model._meta.pk.get_attname_column()[1]}
                )
            )
            action_old = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,
                     self.this_model._meta.pk.get_attname_column()[1]),
                    **{self.field.get_attname_column()[1]: "OLD.%s" % self.other_model._meta.pk.get_attname_column()[1]}
                )
            )
            trigger_list.extend((
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using),
            ))
            if self.other_field:
                trigger_list.append(
                    triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using,
                                     [self.other_field]))

        if self.type == "backward":
            # With backward relations a change in ``other_model`` can affect
            # only one or two instances of ``this_model``.
            # If the ``other_model`` instance changes the value its ForeignKey
            # pointing to ``this_model`` both the old and the new related instance
            # are affected, otherwise only the one it is pointing to is affected.
            action_new = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "NEW.%s" % self.field.get_attname_column()[1],
                )
            )
            action_old = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "OLD.%s" % self.field.get_attname_column()[1],
                )
            )
            trigger_list.extend((
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using),
            ))
            if self.other_field:
                trigger_list.append(
                    triggers.Trigger(self.other_model, "after", "update", [action_new, action_old], content_type, using,
                                     [self.other_field]))

        if "m2m" in self.type:
            # The two directions of M2M relations only differ in the column
            # names used in the intermediate table.
            if "forward" in self.type:
                column_name = self.field.m2m_column_name()
                reverse_column_name = self.field.m2m_reverse_name()
            if "backward" in self.type:
                column_name = self.field.m2m_reverse_name()
                reverse_column_name = self.field.m2m_column_name()

            # The first part of a M2M dependency is exactly like a backward
            # ForeignKey dependency. ``this_model`` is backward FK related
            # to the intermediate table.
            action_m2m_new = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "NEW.%s" % column_name,
                )
            )
            action_m2m_old = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "OLD.%s" % column_name,
                )
            )

            trigger_list.extend((
                triggers.Trigger(self.field, "after", "update", [action_m2m_new, action_m2m_old], content_type, using),
                triggers.Trigger(self.field, "after", "insert", [action_m2m_new], content_type, using),
                triggers.Trigger(self.field, "after", "delete", [action_m2m_old], content_type, using),
            ))

            if isinstance(self.field, models.ManyToManyField) and self.other_field:
                # Additionally to the dependency on the intermediate table
                # ``this_model`` is dependant on updates to the ``other_model``-
                # There is no need to track insert or delete events here,
                # because a relation can only be created or deleted by
                # by modifying the intermediate table.
                #
                # Generic relations are excluded because they have the
                # same m2m_table and model table.
                action_new = triggers.TriggerActionInsert(
                    model=DirtyInstance,
                    columns=("content_type_id", "object_id"),
                    values=triggers.TriggerNestedSelect(
                        self.field.m2m_db_table(),
                        (content_type, column_name),
                        **{reverse_column_name: "NEW.id"}
                    )
                )
                trigger_list.append(
                    triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using,
                                     [self.other_field]))

        return trigger_list



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

depend_on = make_depend_decorator(CallbackDependOnField)