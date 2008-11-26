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

    def __init__(self,depend,func):
        """
        Makes sure self.depend is always a list.
        """
        if isinstance(depend,list):
            self.depend = depend
        else:
            self.depend = [depend]
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
            for dependency in self.depend:
                self.qs |= dependency.resolve(old_instance)

    def post_handler(self,sender,instance,*args,**kwargs):
        """
        Does the same as pre_handler, but gives the resolver opportunity
        to examine the new version of 'instance'.
        """
        for dependency in self.depend:
            self.qs |= dependency.resolve(instance)
        self.update(self.qs.distinct())

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
        for dependency in self.depend:
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
        for instance in qs:
            instance.save()

def rebuildall():
    """
    Updates all models containing denormalized fields.
    Used by the 'denormalize' management command.
    """
    global alldenorms
    for denorm in alldenorms:
        denorm.update(denorm.model.objects.all())

def denormalized(DBField,*args,**kwargs):
    try:
        depend = kwargs['depend']
        del kwargs['depend']
    except:
        depend = []

    class DenormDBField(DBField):
        def contribute_to_class(self,cls,*args,**kwargs):
            global alldenorms
            self.denorm.model = cls
            models.signals.class_prepared.connect(self.denorm.setup,sender=cls)
            DBField.contribute_to_class(self,cls,*args,**kwargs)

    def deco(func):
        global alldenorms
        denorm = Denorm(depend,func)
        alldenorms += [denorm]
        dbfield = DenormDBField(*args,**kwargs)
        dbfield.denorm = denorm
        return dbfield
    return deco
