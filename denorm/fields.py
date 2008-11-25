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

        def pre_handler(sender,instance,**kwargs):
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
            pre_handler.denorm.qs = pre_handler.denorm.model.objects.none()
            if old_instance:
                for dependency in pre_handler.denorm.depend:
                    pre_handler.denorm.qs |= dependency.resolve(old_instance)
        self.pre_handler = pre_handler
        self.pre_handler.denorm = self

        def post_handler(sender,instance,*args,**kwargs):
            """
            Does the same as pre_handler, but gives the resolver opportunity
            to examine the new version of 'instance'.
            """
            for dependency in post_handler.denorm.depend:
                self.qs |= dependency.resolve(instance)
            post_handler.denorm.update(self.qs.distinct())
        self.post_handler = post_handler
        self.post_handler.denorm = self

        def self_save_handler(sender,instance,**kwargs):
            """
            Updated the value of the denormalized field
            in 'instance' before it gets saved.
            """
            setattr(instance,self_save_handler.denorm.func.__name__,self_save_handler.denorm.func(instance))
        self.self_save_handler = self_save_handler
        self.self_save_handler.denorm = self

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
        depend = None

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
