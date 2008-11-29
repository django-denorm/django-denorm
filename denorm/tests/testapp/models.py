
from django.db import models
from denorm import *


class Forum(models.Model):
    
    title = models.CharField(max_length=255)
    
    # Simple count() aggregate
    @denormalized(models.IntegerField)
    @depend_on_related('Post')
    def post_count(self):
        return self.post_set.count()


class Post(models.Model):
    
    forum = models.ForeignKey(Forum, blank=True, null=True)
    
    # Brings down the forum title
    @denormalized(models.CharField, max_length=255)
    @depend_on_related(Forum)
    def forum_title(self):
        return self.forum.title


class Attachment(models.Model):
    
    post = models.ForeignKey(Post)

