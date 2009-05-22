# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic



class DirtyInstance(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(blank=True,null=True)
    content_object = generic.GenericForeignKey(fk_field="object_id")

    class Meta:
        unique_together = (('object_id','content_type'),)

    def __unicode__(self):
        return u'DirtyInstance: %s,%s' % (self.content_type,self.object_id)
