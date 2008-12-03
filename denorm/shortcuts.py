from django.db import models
from denorm.fields import denormalized
from denorm.dependencies import DependOnRelated

def CountField(model,manager,fk_name=None):

    countfield = denormalized(models.IntegerField)(lambda i:getattr(i,manager).count())
    dependency = DependOnRelated(model)
    countfield.denorm.depend = [dependency]

    return countfield

