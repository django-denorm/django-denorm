
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

    @denormalized(models.TextField)
    @depend_on_related('self')
    def path(self):
        if self.parent_forum:
            return self.parent_forum.path+self.title+'/'
        else:
            return '/'+self.title+'/'


class Post(models.Model):

    forum = models.ForeignKey(Forum, blank=True, null=True)
    author = models.ForeignKey('Member', blank=True, null=True)
    response_to = models.ForeignKey('self',blank=True,null=True,related_name='responses')

    attachment_count = CountField('Attachment','attachment_set')

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

    @denormalized(models.PositiveIntegerField)
    @depend_on_related('self',type='backward')
    def response_count(self):
        rcount = self.responses.count()
        rcount += sum((x.response_count for x in self.responses.all()))
        return rcount


class Attachment(models.Model):

    post = models.ForeignKey(Post,blank=True,null=True)

class Member(models.Model):

    first_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)

    @denormalized(models.CharField,max_length=255)
    def full_name(self):
        return u"%s %s"% (self.first_name, self.name)
