from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from denorm.fields import denormalized
from denorm.dependencies import depend_on_related,depend_on_q

class Gallery(models.Model):
    name = models.CharField(max_length=100)

    # This field aggregates usernames of the Pictures
    # in the Gallery. 'depend_on_related' detects that
    # 'Gallery' and 'Picture' are related through a
    # reverse ForeignKey, and updates the affected Gallery
    # when a related Picture changes
    @denormalized(models.TextField,blank=True)
    @depend_on_related('Picture')
    def users(self):
        return ', '.join(p.owner_username for p in self.picture_set.all())

    # Just another use case, this works the same as the field above.
    @denormalized(models.PositiveIntegerField)
    @depend_on_related('Picture')
    def picture_count(self):
        return self.picture_set.count()

    # This field holds the total number of comments made on
    # all Pictures in the Gallery.
    # For more complex dependencies like this 'depend_on_q' can be used.
    # When a 'Comment' changes the provided function (lambda i:...)
    # gets called with the instance being changed as argument.
    # This function must return a Q object that will be used in a
    # filter() to determine which galleries need updating.
    # the filter looks like:
    # Gallery.objects.filter(func(instance))
    # where 'func' is the lambda function and instance the changing
    # instance.
    # Additionaly a Gallery's comment count needs to be updated when
    # pictures get moved or deleted, so it depends on related pictures too.
    @denormalized(models.PositiveIntegerField)
    @depend_on_q('Comment',lambda i: Q(pk=i.picture.gallery.pk))
    @depend_on_related('Picture')
    def picture_comment_count(self):
        return Comment.objects.filter(picture__gallery=self).count()

    def __unicode__(self):
        return self.name

class Picture(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User)
    image = models.ImageField(upload_to='photos')
    gallery = models.ForeignKey('Gallery')

    # This has the same effect like a MirrorField
    # the owner's username just gets copied here.
    # depend_on_related detects forward ForeignKeys
    # as well.
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

    # A small example of depending on multiple related models.
    @denormalized(models.CharField,max_length=100)
    @depend_on_related(Picture)
    @depend_on_related(User)
    def title(self):
        return u'Comment on %s by %s' % (self.picture.name,self.author)

    def __unicode__(self):
        return self.title
