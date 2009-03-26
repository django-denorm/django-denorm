# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic



class DirtyInstance(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    old_object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey(fk_field="object_id")
    old_content_object = generic.GenericForeignKey(fk_field="old_object_id")
