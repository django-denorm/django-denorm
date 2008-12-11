
from django.db import models
from denorm import *


class Forum(models.Model):
    
    title = models.CharField(max_length=255)
    
    # Simple count() aggregate
    post_count = CountField('Post','post_set')

    @denormalized(models.CharField,max_length=255)
    @depend_on_related('Post')
    def authors(self):
        return ', '.join((m.author_name for m in self.post_set.all()))

    # lets say this forums supports subforums, sub-subforums and so forth
    # so we can test depend_on_related('self') (for tree structures).
    parent_forum = models.ForeignKey('self',blank=True,null=True)

    @denormalized(models.CharField,max_length=255)
    @depend_on_related('self')
    def path(self):
        if self.parent_forum:
            return self.parent_forum.path+self.title+'/'
        else:
            return '/'+self.title+'/'
    

class Post(models.Model):
    
    forum = models.ForeignKey(Forum, blank=True, null=True)
    author = models.ForeignKey('Member', blank=True, null=True)
    
    # Brings down the forum title
    @denormalized(models.CharField, max_length=255)
    @depend_on_related(Forum)
    def forum_title(self):
        return self.forum.title


    @denormalized(models.CharField, max_length=255)
    @depend_on_related('Member')
    def author_name(self):
        if self.author:
            return self.author.name
        else: 
            return ''


class Attachment(models.Model):
    
    post = models.ForeignKey(Post)


class Member(models.Model):

    name = models.CharField(max_length=255)
