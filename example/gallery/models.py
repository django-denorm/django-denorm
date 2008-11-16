from django.db import models
from django.contrib.auth.models import User
from denorm.fields import denormalized


class Picture(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User)
    image = models.ImageField(upload_to='photos')
    gallery = models.ForeignKey('Gallery')

    def __unicode__(self):
        return self.name


class Gallery(models.Model):
    name = models.CharField(max_length=100)

    @denormalized(models.TextField,blank=True,depend=[Picture])
    def users(sender,instance,**kwargs):
        instance.gallery.users = ', '.join(str(p.owner) for p in instance.gallery.picture_set.all())
        instance.gallery.save()

    def __unicode__(self):
        return self.name
