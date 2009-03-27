# -*- coding: utf-8 -*-
from django.db import models
from denorm import monkeypatches

# remember all denormalizations.
# this is used to rebuild all denormalized values in the whole DB
alldenorms = []

class Denorm:
    """
    Handles the denormalization of one field.
    Everytime some model instances are updated a queryset is build, that will contain
    all instances of the model containing the field that may need to get
    updated.
    This is done by passing a QuerySet containing all instances beeing
    updated into the resolve() method of all DenormDependency
    subclass instances in 'depend', and combining the results with logical OR.
    """

    def __init__(self,func):
        if not hasattr(func,'depend'):
            func.depend = []
        self.func = func
        self.updating = set()

    def self_save_handler(self,sender,instance,**kwargs):
        """
        Updates the value of the denormalized field
        in 'instance' before it gets saved.
        """
        if instance.pk not in self.updating:
            setattr(instance,self.fieldname,self.func(instance))

    def setup(self,**kwargs):
        """
        Calls setup() on all DenormDependency resolvers
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
            if not instance.pk in self.updating:
                # we need to keep track of the instances this denorm updates
                # to ensure we update them only once. This protects us from endless
                # updates that could otherwise occur with cyclic dependencies.
                # additionally we only write new values to the DB if they actually
                # changed
                new_value = self.func(instance)
                if not getattr(instance,self.fieldname) == new_value:
                    setattr(instance,self.fieldname,new_value)
                    self.updating.add(instance.pk)
                    instance.save()
                    self.updating.remove(instance.pk)

def rebuildall():
    """
    Updates all models containing denormalized fields.
    Used by the 'denormalize' management command.
    """
    global alldenorms
    for denorm in alldenorms:
        denorm.update(denorm.model.objects.all())

def install_triggers():
    from denorm.triggers import TriggerSet
    triggerset = TriggerSet()
    global alldenorms
    for denorm in alldenorms:
        for dependency in denorm.func.depend:
            triggerset.append(dependency.get_triggers())
    triggerset.install()

def flush():
    from denorm.models import DirtyInstance
    while True:
        try:
            dirty_instance = DirtyInstance.objects.all()[0]
        except:
            return

        if dirty_instance.content_object:
            dirty_instance.content_object.save()

        DirtyInstance.objects.filter(object_id__isnull=True).delete()
        DirtyInstance.objects.filter(content_type=dirty_instance.content_type,
            object_id=dirty_instance.object_id).delete()


def denormalized(DBField,*args,**kwargs):

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
        denorm = Denorm(func)
        dbfield = DenormDBField(*args,**kwargs)
        dbfield.denorm = denorm
        return dbfield
    return deco
