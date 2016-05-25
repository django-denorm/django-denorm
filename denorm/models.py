# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.contenttypes.models import ContentType
try:
    from django.contrib.contenttypes.fields import GenericForeignKey
except ImportError:
    from django.contrib.contenttypes.generic import GenericForeignKey


class DirtyInstance(models.Model):
    """
    Holds a reference to a model instance that may contain inconsistent data
    that needs to be recalculated.
    DirtyInstance instances are created by the insert/update/delete triggers
    when related objects change.
    """
    class Meta:
        app_label="denorm"
        unique_together = (('content_type', 'object_id', ), )

    content_type = models.ForeignKey(ContentType)
    object_id = models.TextField(blank=True, null=True, db_index=True)
    content_object = GenericForeignKey()

    def __str__(self):
        return u'DirtyInstance: %s,%s' % (self.content_type, self.object_id)

    def __unicode__(self):
        return u'DirtyInstance: %s, %s' % (self.content_type, self.object_id)
