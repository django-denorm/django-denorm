# -*- coding: utf-8 -*-
from denorm.helpers import find_fk

class DenormDependency:
    def resolve(instance):
        return None

class ForwardForeignKey(DenormDependency):
    def __init__(self,model,foreign_key=None):
        self.other_model = model
        self.foreign_key = foreign_key

    def resolve(self,instance):
        if isinstance(instance,self.other_model):
            return self.this_model.objects.filter(**{self.foreign_key:instance.id})
        else:
            return self.this_model.objects.none()

    def setup(self,this_model, **kwargs):
        self.this_model = this_model
        self.foreign_key = find_fk(this_model,self.other_model,self.foreign_key)

class BackwardForeignKey(DenormDependency):
    def __init__(self,model,foreign_key=None):
        self.other_model = model
        self.foreign_key = foreign_key

    def resolve(self,instance):
        if isinstance(instance,self.other_model):
            id = getattr(instance,self.foreign_key).id
            return self.this_model.objects.filter(id__exact=id)
        else:
            return self.this_model.objects.none()

    def setup(self,this_model, **kwargs):
        self.this_model = this_model
        self.foreign_key = find_fk(self.other_model,this_model,self.foreign_key)

