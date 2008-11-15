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

        def saverelay(*args,**kwargs):
            kwargs['deleted'] = False
            func(*args,**kwargs)
        self.saverelay = saverelay
        def deleterelay(*args,**kwargs):
            kwargs['deleted'] = True
            func(*args,**kwargs)
        self.deleterelay = deleterelay

        for sender in self.depend:
            models.signals.pre_save.connect(pre_handler,sender)
            models.signals.post_save.connect(self.saverelay,sender)
            models.signals.post_delete.connect(self.deleterelay,sender)

    def rebuild(self):
        for model in self.depend:
            for object in model.objects.all():
                self.saverelay(sender=model,instance=object,created=True)

def rebuildall():
    global alldenorms
    for denorm in alldenorms:
        denorm.rebuild()
    
from django.db import models
def denormalized(DBField,depend):
    def deco(func):
        global alldenorms
        alldenorms += [Denorm(depend,func)]
        return DBField
    return deco
