# -*- coding: utf-8 -*-
from django.db import models

alldenorms = []

class Denorm:
    def __init__(self,depend,func):
        if isinstance(depend,list):
            self.depend = depend
        else:
            self.depend = [depend]
        self.func = func

        def pre_handler(sender,instance,**kwargs):
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
            for dependency in post_handler.denorm.depend:
                self.qs |= dependency.resolve(instance)
            post_handler.denorm.update(self.qs.distinct())
        self.post_handler = post_handler
        self.post_handler.denorm = self

        def self_save_handler(sender,instance,**kwargs):
            setattr(instance,self_save_handler.denorm.func.__name__,self_save_handler.denorm.func(instance))
        self.self_save_handler = self_save_handler
        self.self_save_handler.denorm = self

    def setup(self,**kwargs):
        for dependency in self.depend:
            dependency.setup(self.model)

        models.signals.pre_save.connect(self.pre_handler)
        models.signals.post_save.connect(self.post_handler)
        models.signals.post_delete.connect(self.post_handler)

        models.signals.pre_save.connect(self.self_save_handler,sender=self.model)

    def update(self,qs):
        for instance in qs:
            instance.save()

def rebuildall():
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
