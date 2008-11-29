# -*- coding: utf-8 -*-
from django.db import models

# remember all denormalizations.
# this is used to rebuild all denormalized values in the whole DB
alldenorms = []

class Denorm:
    """
    Handles the denormalization of one field.
    Everytime some model instance is saved a queryset is build, that will contain
    all instances of the model containing the field that may need to get
    updated.
    This is done by passing the instance beeing saved into the resolve()
    method of all DenormDependency subclass instances in 'depend',
    and combining the results with logical OR.
    """

    def __init__(self,func):
        if not hasattr(func,'depend'):
            func.depend = []
        self.func = func

    def pre_handler(self,sender,instance,**kwargs):
        """
        Gives the DenormDependency resolver a chance to
        work before the instance is altered.
        Without this, a changed backwards ForeignKey relation
        for example, will result in an incorrect value in the
        instance the ForeignKey was pointing to before the save.
        """
        try:
            old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            old_instance = None
        self.qs = self.model.objects.none()
        if old_instance:
            for dependency in self.func.depend:
                self.qs |= dependency.resolve(old_instance)

    def post_handler(self,sender,instance,*args,**kwargs):
        """
        Does the same as pre_handler, but gives the resolver opportunity
        to examine the new version of 'instance'.
        """
        # If this is a save from an outer denorm, skip it
        if hasattr(instance, "_denorm_skip"):
            return
        # Use every dependency.
        for dependency in self.func.depend:
            self.qs |= dependency.resolve(instance)
        self.update(self.qs)

    def self_save_handler(self,sender,instance,**kwargs):
        """
        Updated the value of the denormalized field
        in 'instance' before it gets saved.
        """
        setattr(instance,self.func.__name__,self.func(instance))

    def setup(self,**kwargs):
        """
        Calls setup() on all DenormDependency resolvers
        and connects all needed signals.
        """
        for dependency in self.func.depend:
            dependency.setup(self.model)

        models.signals.pre_save.connect(self.pre_handler)
        models.signals.post_save.connect(self.post_handler)
        models.signals.post_delete.connect(self.post_handler)

        models.signals.pre_save.connect(self.self_save_handler,sender=self.model)

    def update(self,qs):
        """
        Updates the denormalizations in all instances in the queryset 'qs'.
        As the update itself is triggered by the pre_save signal, we just
        need to save() all instances.
        """
        for instance in qs.distinct():
            # Save, but set an attribute to avoid triggering the handler again
            instance._denorm_skip = True
            instance.save()
            del instance._denorm_skip


def rebuildall():
    """
    Updates all models containing denormalized fields.
    Used by the 'denormalize' management command.
    """
    global alldenorms
    for denorm in alldenorms:
        denorm.update(denorm.model.objects.all())

def denormalized(DBField,*args,**kwargs):

    class DenormDBField(DBField):
        
        """
        Special subclass of the given DBField type, with a few extra additions.
        """
        
        def contribute_to_class(self,cls,*args,**kwargs):
            self.denorm.model = cls
            self.field_args = (args, kwargs)
            models.signals.class_prepared.connect(self.denorm.setup,sender=cls)
            DBField.contribute_to_class(self,cls,*args,**kwargs)
    
        def south_field_definition(self):
            """
            Because this field will be defined as a decorator, give
            South hints on how to recreate it for database use.
            """
            if DBField.__module__.startswith("django.db.models.fields"):
                arglist = [repr(x) for x in args]
                kwlist = ["%s=%r" % (x, y) for x, y in kwargs.items()]
                return "%s(%s)" % (
                    DBField.__name__,
                    ", ".join(arglist + kwlist)
                )

    def deco(func):
        global alldenorms
        denorm = Denorm(func)
        alldenorms += [denorm]
        dbfield = DenormDBField(*args,**kwargs)
        dbfield.denorm = denorm
        return dbfield
    return deco
