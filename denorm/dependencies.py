# -*- coding: utf-8 -*-
from denorm.helpers import find_fk
from django.db.models.fields.related import add_lazy_relation

def make_depend_decorator(Resolver):
    def decorator(*args,**kwargs):
        def deco(func):
            if not hasattr(func,'depend'):
                func.depend = []
            func.depend += [Resolver(*args,**kwargs)]
            return func
        return deco
    return decorator

class DenormDependency:
    def resolve(*args,**kwargs):
        return None
    def setup(*args,**kwargs):
        pass

class DependOnRelated(DenormDependency):
    def __init__(self,model,foreign_key=None):
        self.other_model = model
        self.foreign_key = foreign_key
        self.type = 'none'

    def resolve_backward(self,instance):
        if isinstance(instance,self.other_model):
            id = getattr(instance,self.foreign_key).id
            return self.this_model.objects.filter(id__exact=id)
        else:
            return self.this_model.objects.none()

    def resolve_forward(self,instance):
        if isinstance(instance,self.other_model):
            return self.this_model.objects.filter(**{self.foreign_key:instance.id})
        else:
            return self.this_model.objects.none()

    def resolve(self,instance):
        if self.type == 'forward':
            return self.resolve_forward(instance)
        elif self.type == 'backward':
            return self.resolve_backward(instance)

    def setup(self,this_model, **kwargs):
        self.this_model = this_model
        if isinstance(self.other_model,(str,unicode)):
            add_lazy_relation(self.this_model, None, self.other_model, self.resolved_model)
        else:
            self.resolved_model(None,self.other_model,None)

    def resolved_model(self, data, model, cls):
        self.other_model = model
        try:
            self.foreign_key = find_fk(self.this_model,self.other_model,self.foreign_key)
            self.type = 'forward'
        except ValueError:
            self.foreign_key = find_fk(self.other_model,self.this_model,self.foreign_key)
            self.type = 'backward'
depend_on_related = make_depend_decorator(DependOnRelated)

class DependOnQ(DenormDependency):
    def __init__(self,model,qgen):
        self.other_model = model
        self.qgen = qgen

    def resolve(self, instance):
        if isinstance(instance,self.other_model):
            return self.this_model.objects.filter(self.qgen(instance))
        else:
            return self.this_model.objects.none()

    def setup(self,this_model, **kwargs):
        self.this_model = this_model
        if isinstance(self.other_model,(str,unicode)):
            add_lazy_relation(self.this_model, None, self.other_model, self.resolved_model)
        else:
            self.resolved_model(None,self.other_model,None)

    def resolved_model(self, data, model, cls):
        self.other_model = model
depend_on_q = make_depend_decorator(DependOnQ)
