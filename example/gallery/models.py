from django.db import models
from django.contrib.auth.models import User
from denorm.fields import denormalized
from denorm.dependencies import depend_on_related


class Gallery(models.Model):
    name = models.CharField(max_length=100)

    @denormalized(models.TextField,blank=True)
    @depend_on_related('Picture')
    def users(self):
        return ', '.join(p.owner_username for p in self.picture_set.all())

    @denormalized(models.PositiveIntegerField,default=0)
    @depend_on_related('Picture')
    def picture_count(self):
        return self.picture_set.count()

    def __unicode__(self):
        return self.name

class Picture(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User)
    image = models.ImageField(upload_to='photos')
    gallery = models.ForeignKey('Gallery')

    @denormalized(models.CharField,max_length=100)
    @depend_on_related(User)
    def owner_username(self):
        return self.owner.username

    def __unicode__(self):
        return self.name

class Comment(models.Model):
    text = models.TextField()
    picture = models.ForeignKey(Picture)
    author = models.ForeignKey(User)

    @denormalized(models.CharField,max_length=100)
    @depend_on_related(Picture)
    @depend_on_related(User)
    def title(self):
        return u'Comment on %s by %s' % (self.picture.name,self.author)

    def __unicode__(self):
        return self.title
