# -*- coding: utf-8 -*-
alldenorms = []

def pre_handler(sender,instance,**kwargs):
    try:
        instance._old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._old_instance = None

class Denorm:
    def __init__(self,depend,func):
        self.depend = depend
        self.func = func

        def saverelay(sender,instance,*args,**kwargs):
            kwargs['deleted'] = False
            if sender in saverelay.denorm.depend:
                if not hasattr(instance,'_denorm_done'):
                    instance._denorm_done = True
                    func(sender,instance,*args,**kwargs)
        self.saverelay = saverelay
        self.saverelay.denorm = self

        def deleterelay(sender,*args,**kwargs):
            kwargs['deleted'] = True
            if sender in deleterelay.denorm.depend:
                func(sender,*args,**kwargs)
        self.deleterelay = deleterelay
        self.deleterelay.denorm = self

        models.signals.pre_save.connect(pre_handler)
        models.signals.post_save.connect(self.saverelay)
        models.signals.post_delete.connect(self.deleterelay)

    def rebuild(self):
        for model in self.depend:
            for object in model.objects.all():
                self.saverelay(sender=model,instance=object,created=True)

def rebuildall():
    global alldenorms
    for denorm in alldenorms:
        denorm.rebuild()

from django.db import models
def denormalized(DBField,*args,**kwargs):
    try:
        depend = kwargs['depend']
        del kwargs['depend']
    except:
        depend = ['self']

    class DenormDBField(DBField):
        def contribute_to_class(self,cls,*args,**kwargs):
            global alldenorms
            if "self" in alldenorms[-1].depend:
                alldenorms[-1].depend += [cls]
                alldenorms[-1].depend.remove("self")
            DBField.contribute_to_class(self,cls,*args,**kwargs)

    def deco(func):
        global alldenorms
        alldenorms += [Denorm(depend,func)]
        return DenormDBField(*args,**kwargs)
    return deco
