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

    @denormalized(models.TextField,blank=True,depend=['self',Picture])
    def users(sender,instance,created,**kwargs):
        if sender is Picture:
            if not created:
                new = ', '.join(str(p.owner) for p in instance._old_instance.gallery.picture_set.all())
                instance._old_instance.gallery.users = new
                instance._old_instance.gallery.save()
            new = ', '.join(str(p.owner) for p in instance.gallery.picture_set.all())
            instance.gallery.users = new
            instance.gallery.save()
        if sender is Gallery:
            instance.users = ', '.join(str(p.owner) for p in instance.picture_set.all())
            instance.save()

    def __unicode__(self):
        return self.name
