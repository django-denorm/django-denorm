# -*- coding: utf-8 -*-
from denorm.helpers import find_fks,find_m2ms
from django.db.models.fields import related
from denorm.models import DirtyInstance
from django.contrib.contenttypes.models import ContentType
from denorm.db import triggers


class DenormDependency(object):

    """
    Base class for real dependency classes.
    """

    def get_triggers(self):
        """
        Must return a list of ``denorm.triggers.Trigger`` instances
        """
        return []

    def setup(self, this_model):
        """
        Remembers the model this dependency was declared in.
        """
        self.this_model = this_model

class DependOnRelated(DenormDependency):

    """
    A DenormDependency that handles callbacks depending on fields
    in other models that are related to the dependent model.

    Two models are considered related if there is a ForeignKey or ManyToManyField
    on either of them pointing to the other one.
    """

    def __init__(self,model,foreign_key=None,type=None):
        self.other_model = model
        self.fk_name = foreign_key
        self.type = type

    def get_triggers(self):
        content_type = str(ContentType.objects.get_for_model(self.this_model).id)

        if self.type == "forward":
            # With forward relations many instances of ``this_model``
            # may be related to one instance of ``other_model``
            # so we need to do a nested select query in the trigger
            # to find them all.
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,"id"),
                    **{self.field.attname:"NEW.id"}
                )
            )
            action_old = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,"id"),
                    **{self.field.attname:"OLD.id"}
                )
            )
            return [
                triggers.Trigger(self.other_model,"after","update",[action_new]),
                triggers.Trigger(self.other_model,"after","insert",[action_new]),
                triggers.Trigger(self.other_model,"after","delete",[action_old]),
            ]

        if self.type == "backward":
            # With backward relations a change in ``other_model`` can affect
            # only one or two instances of ``this_model``.
            # If the ``other_model`` instance changes the value its ForeignKey
            # pointing to ``this_model`` both the old and the new related instance
            # are affected, otherwise only the one it is pointing to is affected.
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "NEW.%s" % self.field.attname,
                )
            )
            action_old = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "OLD.%s" % self.field.attname,
                )
            )
            return [
                triggers.Trigger(self.other_model,"after","update",[action_new,action_old]),
                triggers.Trigger(self.other_model,"after","insert",[action_new]),
                triggers.Trigger(self.other_model,"after","delete",[action_old]),
            ]

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
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "NEW.%s" % column_name,
                )
            )
            action_m2m_old = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "OLD.%s" % column_name,
                )
            )

            # Additionally to the dependency on the intermediate table
            # ``this_model`` is dependant on updates to the ``other_model``-
            # There is no need to track insert or delete events here,
            # because a relation can only be created or deleted by
            # by modifying the intermediate table.
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.field.m2m_db_table(),
                    (content_type,column_name),
                    **{reverse_column_name:"NEW.id"}
                )
            )

            return [
                triggers.Trigger(self.field,"after","update",[action_m2m_new,action_m2m_old]),
                triggers.Trigger(self.field,"after","insert",[action_m2m_new]),
                triggers.Trigger(self.field,"after","delete",[action_m2m_old]),
                triggers.Trigger(self.other_model,"after","update",[action_new]),
            ]

        return []


    def setup(self, this_model):
        super(DependOnRelated,self).setup(this_model)

        # FIXME: this should not be necessary
        if self.other_model == related.RECURSIVE_RELATIONSHIP_CONSTANT:
            self.other_model = self.this_model

        if isinstance(self.other_model,(str,unicode)):
            # if ``other_model`` is a string, it certainly is a lazy relation.
            related.add_lazy_relation(self.this_model, None, self.other_model, self.resolved_model)
        else:
            # otherwise it can be resolved directly
            self.resolved_model(None,self.other_model,None)

    def resolved_model(self, data, model, cls):
        """
        Does all the initialization that had to wait until we knew which
        model we depend on.
        """
        self.other_model = model

        # Create a list of all ForeignKeys and ManyToManyFields between both related models, in both directions
        candidates  = [('forward',fk) for fk in find_fks(self.this_model,self.other_model,self.fk_name)]
        candidates += [('backward',fk) for fk in find_fks(self.other_model,self.this_model,self.fk_name)]
        candidates += [('forward_m2m',fk) for fk in find_m2ms(self.this_model,self.other_model,self.fk_name)]
        candidates += [('backward_m2m',fk) for fk in find_m2ms(self.other_model,self.this_model,self.fk_name)]

        # If a relation type was given (forward,backward,forward_m2m or backward_m2m),
        # filter out all relations that do not match this type.
        candidates = [x for x in candidates if not self.type or self.type == x[0]]

        if len(candidates) > 1:
            raise ValueError("%s has more than one ForeignKey or ManyToManyField to %s (or reverse); cannot auto-resolve."
                             % (self.this_model, self.other_model))
        if not candidates:
            raise ValueError("%s has no ForeignKeys or ManyToManyFields to %s (or reverse); cannot auto-resolve."
                             % (self.this_model, self.other_model))

        # Now the candidates list contains exactly one item, thats our winner.
        self.type, self.field = candidates[0]


def make_depend_decorator(Class):
    """
    Create a decorator that attaches an instance of the given class
    to the decorated function, passing all remaining arguments to the classes
    __init__.
    """
    def decorator(*args,**kwargs):
        def deco(func):
            if not hasattr(func,'depend'):
                func.depend = []
            func.depend += [Class(*args,**kwargs)]
            return func
        return deco
    return decorator

depend_on_related = make_depend_decorator(DependOnRelated)

