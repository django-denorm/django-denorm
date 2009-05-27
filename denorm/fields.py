# -*- coding: utf-8 -*-
from django.db import models

# remember all denormalizations.
# this is used to rebuild all denormalized values in the whole DB
alldenorms = []

class Denorm:

    """
    Handles the denormalization of one field.
    """

    def __init__(self,func):
        # ensure self.func is always a list
        if not hasattr(func,'depend'):
            func.depend = []
        self.func = func

    def self_save_handler(self,sender,instance,**kwargs):
        """
        Updates the value of the denormalized field
        in 'instance' before it gets saved.
        """
        setattr(instance,self.fieldname,self.func(instance))

    def setup(self,**kwargs):
        """
        Adds 'self' to the global denorm list,
        calls setup() on all DenormDependency resolvers
        and connects all needed signals.
        """
        global alldenorms
        alldenorms += [self]

        for dependency in self.func.depend:
            dependency.setup(self.model)

        models.signals.pre_save.connect(self.self_save_handler,sender=self.model)

    def update(self,qs):
        """
        Updates the denormalizations in all instances in the queryset 'qs'.
        """
        for instance in qs.distinct():
            # only write new values to the DB if they actually changed
            new_value = self.func(instance)
            if not getattr(instance,self.fieldname) == new_value:
                setattr(instance,self.fieldname,new_value)
                instance.save()
        flush()

    def get_triggers(self):
        """
        Creates a list of all triggers needed to keep track of changes
        to fields this denorm depends on.
        """
        from denorm.db import triggers
        from django.contrib.contenttypes.models import ContentType
        from denorm.models import DirtyInstance

        content_type = str(ContentType.objects.get_for_model(self.model).id)

        # Create a trigger that marks any updated or newly created
        # instance of the model containing the denormalized field
        # as dirty.
        # This is only really needed if the instance was changed without
        # using the ORM or if it was part of a bulk update.
        # In those cases the self_save_handler won't get called by the
        # pre_save signal, so we need to ensure flush() does this later.
        action = triggers.TriggerActionInsert(
            model = DirtyInstance,
            columns = ("content_type_id","object_id"),
            values = (content_type,"NEW.id")
        )
        trigger_list = [
            triggers.Trigger(self.model,"after","update",[action]),
            triggers.Trigger(self.model,"after","insert",[action]),
        ]

        # Get the triggers of all DenormDependency instances attached
        # to our callback.
        for dependency in self.func.depend:
            trigger_list += dependency.get_triggers()

        return trigger_list

def rebuildall():
    """
    Updates all models containing denormalized fields.
    Used by the 'denormalize' management command.
    """
    global alldenorms
    for denorm in alldenorms:
        denorm.update(denorm.model.objects.all())

def install_triggers():
    """
    Installs all required triggers in the database
    """
    from denorm.db import triggers
    global alldenorms

    # Use a TriggerSet to ensure each event gets just one trigger
    triggerset = triggers.TriggerSet()
    for denorm in alldenorms:
        triggerset.append(denorm.get_triggers())
    triggerset.install()

def flush():
    """
    Updates all model instances marked as dirty by the DirtyInstance
    model.
    After this method finishes the DirtyInstance table is empty and
    all denormalized fields have consistent data.
    """
    from denorm.models import DirtyInstance

    # Loop until break.
    # We may need multiple passes, because an update on one instance
    # may cause an other instance to be marked dirty (dependency chains)
    while True:
        # Get all dirty markers
        qs = DirtyInstance.objects.all()

        # DirtyInstance table is empty -> all data is consistent -> we're done
        if not qs: break

        # Call save() on all dirty instances, causing the self_save_handler()
        # getting called by the pre_save signal.
        for dirty_instance in qs:
            if dirty_instance.content_object:
                dirty_instance.content_object.save()
            dirty_instance.delete()

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
            DBField.contribute_to_class(self,cls,name,*args,**kwargs)

        def south_field_definition(self):
            """
            the old way of telling south how this field should be
            inserted into migrations, this will be removed soon
            """
            if DBField.__module__.startswith("django.db.models.fields"):
                arglist = [repr(x) for x in args]
                kwlist = ["%s=%r" % (x, y) for x, y in kwargs.items()]
                return "%s(%s)" % (
                    DBField.__name__,
                    ", ".join(arglist + kwlist)
                )

        def south_field_triple(self):
            """
            Because this field will be defined as a decorator, give
            South hints on how to recreate it for database use.
            """
            if DBField.__module__.startswith("django.db.models.fields"):
                return (
                    '.'.join(('models',DBField.__name__)),
                    [repr(x) for x in args],
                    kwargs,
                )

    def deco(func):
        denorm = Denorm(func)
        dbfield = DenormDBField(*args,**kwargs)
        dbfield.denorm = denorm
        return dbfield
    return deco
