from denorm.dependencies import depend_on
from denorm.fields import SumField
import django
from django.db import models
from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from denorm import denormalized, CountField, CacheKeyField, cached
from django.core.cache import cache

class CachedModelA(models.Model):

    b = models.ForeignKey('CachedModelB')

    @cached(cache)
    @depend_on('b__data')
    def cached_data(self):
        return {
            'upper':self.b.data.upper(),
            'lower':self.b.data.lower(),
        }

class CachedModelB(models.Model):
    data = models.CharField(max_length=255)


class Tag(models.Model):
    name = models.CharField(max_length=255)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class TaggedModel(models.Model):
    tags = GenericRelation(Tag)

    @denormalized(models.TextField)
    @depend_on('tags__name')
    def tags_string(self):
        return ', '.join(sorted([t.name for t in self.tags.all()]))

    class Meta:
        abstract = True


class Forum(TaggedModel):

    title = models.CharField(max_length=255)

    # Simple count() aggregate
    post_count = CountField('post_set')

    cachekey = CacheKeyField()
    cachekey.depend_on('post__forum_id')

    @denormalized(models.CharField, max_length=255)
    @depend_on('post__author_name')
    def author_names(self):
        return ', '.join((m.author_name for m in self.post_set.all()))

    @denormalized(models.ManyToManyField, 'Member', null=True, blank=True)
    @depend_on('post__author_id')
    def authors(self):
        return [m.author for m in self.post_set.all() if m.author]

    # let's say this forums supports subforums, sub-subforums and so forth
    # so we can test depend_on_related('self') (for tree structures).
    parent_forum = models.ForeignKey('self', blank=True, null=True)

    @denormalized(models.TextField)
    @depend_on('parent_forum__path')
    @depend_on('title')
    def path(self):
        if self.parent_forum:
            return self.parent_forum.path + self.title + '/'
        else:
            return '/' + self.title + '/'


class Post(TaggedModel):

    forum = models.ForeignKey(Forum, blank=True, null=True)
    author = models.ForeignKey('Member', blank=True, null=True)
    response_to = models.ForeignKey('self', blank=True, null=True, related_name='responses')
    title = models.CharField(max_length=255, blank=True)

    # Brings down the forum title
    @denormalized(models.CharField, max_length=255)
    @depend_on('forum__title')
    def forum_title(self):
        return self.forum.title

    @denormalized(models.CharField, max_length=255)
    @depend_on('author__name')
    def author_name(self):
        if self.author:
            return self.author.name
        else:
            return ''

    @denormalized(models.PositiveIntegerField)
    @depend_on('responses')
    def response_count(self):
        # Work around odd issue during testing with PostgresDB
        if not self.pk:
            return 0
        rcount = self.responses.count()
        rcount += sum((x.response_count for x in self.responses.all()))
        return rcount


class Attachment(models.Model):

    post = models.ForeignKey(Post, blank=True, null=True)

    cachekey = CacheKeyField()
    cachekey.depend_on('post__title')

    @denormalized(models.ForeignKey, Forum, blank=True, null=True)
    @depend_on('post__forum_id')
    def forum(self):
        if self.post and self.post.forum:
            return self.post.forum.pk
        return None


class Member(models.Model):

    first_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    bookmarks = models.ManyToManyField('Post', blank=True)

    cachekey = CacheKeyField()
    cachekey.depend_on('bookmarks__title')

    @denormalized(models.CharField, max_length=255)
    @depend_on('first_name')
    @depend_on('name')
    def full_name(self):
        return u"%s %s" % (self.first_name, self.name)

    @denormalized(models.TextField)
    @depend_on('bookmarks__title')
    def bookmark_titles(self):
        if self.id:
            return '\n'.join([p.title for p in self.bookmarks.all()])


class SkipPost(models.Model):
    # Skip feature test main model.
    text = models.TextField()


class SkipComment(models.Model):
    post = models.ForeignKey(SkipPost)
    text = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class SkipCommentWithoutSkip(SkipComment):
    # Skip feature test model without a skip parameter on an updatable field.
    # he updatable field will not be skipped.
    @denormalized(models.TextField)
    @depend_on('post__text')
    def post_text(self):
        return self.post.text


class SkipCommentWithSkip(SkipComment):
    # Skip feature test model with a skip parameter on an updatable field.
    @denormalized(models.TextField)
    @depend_on('post__text')
    def post_text(self):
        return self.post.text

class SkipCommentWithAttributeSkip(SkipComment):
    @denormalized(models.TextField)
    @depend_on('post__text')
    def post_text(self):
        return self.post.text


if not hasattr(django.db.backend,'sqlite3'):
    class FilterSumModel(models.Model):
        # Simple count() aggregate
        active_item_sum = SumField('counts', field='active_item_count', filter = {'age__gte':18})

    class FilterSumItem(models.Model):
        parent = models.ForeignKey(FilterSumModel, related_name='counts')
        age = models.IntegerField(default=18)
        active_item_count = models.PositiveIntegerField(default=False)


    class FilterCountModel(models.Model):
        # Simple count() aggregate
        active_item_count = CountField('items', filter = {'active__exact':True})

    class FilterCountItem(models.Model):
        parent = models.ForeignKey(FilterCountModel, related_name='items')
        active = models.BooleanField(default=False)

from denorm.denorms import alldenorms
for denorm in alldenorms:
    denorm.setup()