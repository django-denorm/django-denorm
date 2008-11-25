# -*- coding: utf-8 -*-
from denorm.helpers import find_fk

class DenormDependency:
    def resolve(*args,**kwargs):
        return None
    def setup(*args,**kwargs):
        pass

class OnRelated(DenormDependency):
    def __init__(self,model,foreign_key=None):
        self.other_model = model
        self.foreign_key = foreign_key

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
        try:
            self.foreign_key = find_fk(this_model,self.other_model,self.foreign_key)
            self.type = 'forward'
        except ValueError:
            self.foreign_key = find_fk(self.other_model,this_model,self.foreign_key)
            self.type = 'backward'
