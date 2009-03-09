from django.db.models.query import QuerySet
from django.dispatch import Signal

pre_update = Signal(providing_args=['changed_objs',])
post_update = Signal(providing_args=['changed_objs',])

origupdate = QuerySet.update

def newupdate(self,**kwargs):
    pre_update.send(sender=self.model,changed_objs=self)
    origupdate(self,**kwargs)
    post_update.send(sender=self.model,changed_objs=self)

QuerySet.update = newupdate
