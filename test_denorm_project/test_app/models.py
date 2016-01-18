from django.db import connection
from django.conf import settings
from django.db import models
try:
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
except ImportError:
    from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation
from django.contrib import contenttypes
from django.core.cache import cache

from denorm.fields import SumField
from denorm import denormalized, depend_on_related, CountField, CacheKeyField, cached


settings.DENORM_MODEL = 'test_app.RealDenormModel'


class FailingTriggersModelA(models.Model):
    order = models.SmallIntegerField(default=0)  # Fails for SQLite
    SomeWeirdName = models.CharField(max_length=255)  # Fails for PostgreSQL


class FailingTriggersModelB(models.Model):
    a = models.ForeignKey(FailingTriggersModelA)

    @denormalized(models.TextField)
    @depend_on_related(FailingTriggersModelA)
    def SomeWeirdName(self):
        return self.a.SomeWeirdName


class CachedModelA(models.Model):
    b = models.ForeignKey('CachedModelB')

    @cached(cache)
    @depend_on_related('CachedModelB')
    def cached_data(self):
        return {
            'upper': self.b.data.upper(),
            'lower': self.b.data.lower(),
        }


class CachedModelB(models.Model):
    data = models.CharField(max_length=255)


class AbstractDenormModel(models.Model):
    # Skip feature test main model.
    text = models.TextField()

    @denormalized(models.TextField)
    def ham(self):
        return u"Ham and %s" % self.text

    class Meta:
        abstract = True
        app_label = 'test_app'


class DenormModel(AbstractDenormModel):
    @denormalized(models.TextField)
    def spam(self):
        return u"Spam and %s" % self.text

    class Meta(AbstractDenormModel.Meta):
        swappable = 'DENORM_MODEL'


class RealDenormModel(AbstractDenormModel):
    @denormalized(models.TextField)
    def eggs(self):
        return u"Eggs and %s" % self.text

    class Meta(AbstractDenormModel.Meta):
        pass


class Tag(models.Model):
    name = models.CharField(max_length=255)

    content_type = models.ForeignKey(contenttypes.models.ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class TaggedModel(models.Model):
    tags = GenericRelation(Tag)

    @denormalized(models.TextField)
    @depend_on_related(Tag)
    def tags_string(self):
        return ', '.join(sorted([t.name for t in self.tags.all()]))

    class Meta:
        abstract = True


class Forum(TaggedModel):
    title = models.CharField(max_length=255)

    # Simple count() aggregate
    post_count = CountField('post_set')

    cachekey = CacheKeyField()
    cachekey.depend_on_related('Post')

    @denormalized(models.CharField, max_length=255)
    @depend_on_related('Post')
    def author_names(self):
        return ', '.join((m.author_name for m in self.post_set.all()))

    @denormalized(models.ManyToManyField, 'Member', blank=True)
    @depend_on_related('Post')
    def authors(self):
        return [m.author for m in self.post_set.all() if m.author]

    # let's say this forums supports subforums, sub-subforums and so forth
    # so we can test depend_on_related('self') (for tree structures).
    parent_forum = models.ForeignKey('self', blank=True, null=True)

    @denormalized(models.TextField)
    @depend_on_related('self', type='forward')
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
    @depend_on_related(Forum)
    def forum_title(self):
        return self.forum.title

    @denormalized(models.CharField, max_length=255)
    @depend_on_related('Member', foreign_key="author")
    def author_name(self):
        if self.author:
            return self.author.name
        else:
            return ''

    @denormalized(models.PositiveIntegerField)
    @depend_on_related('self', type='backward')
    def response_count(self):
        # Work around odd issue during testing with PostgresDB
        if not self.pk:
            return 0
        rcount = self.responses.count()
        rcount += sum((x.response_count for x in self.responses.all()))
        return rcount


class Attachment(models.Model):
    forum_as_object = False

    post = models.ForeignKey(Post, blank=True, null=True)

    cachekey = CacheKeyField()
    cachekey.depend_on_related('Post')

    @denormalized(models.ForeignKey, Forum, blank=True, null=True)
    @depend_on_related(Post)
    def forum(self):
        if self.post and self.post.forum:
            if self.forum_as_object:
                # if forum_as_object is set, return forum denorm as an object
                return self.post.forum
            else:
                # otherwise, return as a primary key
                return self.post.forum.pk
        return None


class Member(models.Model):
    first_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    bookmarks = models.ManyToManyField('Post', blank=True)

    cachekey = CacheKeyField()
    cachekey.depend_on_related('Post', foreign_key='bookmarks')

    @denormalized(models.CharField, max_length=255)
    def full_name(self):
        return u"%s %s" % (self.first_name, self.name)

    @denormalized(models.TextField, null=True, blank=True)
    @depend_on_related('Post', foreign_key="bookmarks")
    def bookmark_titles(self):
        if self.id:
            return '\n'.join([p.title for p in self.bookmarks.all()])


class SkipPost(models.Model):
    # Skip feature test main model.
    text = models.TextField()


class CallCounter(models.Model):
    @denormalized(models.IntegerField)
    def called_count(self):
        if not self.called_count:
            return 1
        return self.called_count + 1


class CallCounterProxy(CallCounter):
    class Meta:
        proxy = True


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
    @depend_on_related(SkipPost)
    def post_text(self):
        return self.post.text


class SkipCommentWithSkip(SkipComment):
    # Skip feature test model with a skip parameter on an updatable field.
    @denormalized(models.TextField, skip=('updated_on',))
    @depend_on_related(SkipPost)
    def post_text(self):
        return self.post.text


class SkipCommentWithAttributeSkip(SkipComment):
    @denormalized(models.TextField)
    @depend_on_related(SkipPost)
    def post_text(self):
        return self.post.text

    denorm_always_skip = ('updated_on',)


if connection.vendor != "sqlite":
    class FilterSumModel(models.Model):
        # Simple count() aggregate
        active_item_sum = SumField('counts', field='active_item_count', filter={'age__gte': 18})

    class FilterSumItem(models.Model):
        parent = models.ForeignKey(FilterSumModel, related_name='counts')
        age = models.IntegerField(default=18)
        active_item_count = models.PositiveIntegerField(default=False)

    class FilterCountModel(models.Model):
        # Simple count() aggregate
        active_item_count = CountField('items', filter={'active__exact': True}, exclude={'text': ''})

    class FilterCountItem(models.Model):
        parent = models.ForeignKey(FilterCountModel, related_name='items')
        active = models.BooleanField(default=False)
        text = models.CharField(max_length=10, default='')
