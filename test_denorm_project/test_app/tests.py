from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

from django.contrib.auth import get_user_model
User = get_user_model()

import denorm
from denorm import denorms
from test_app import models
import django
from decimal import Decimal

# Use all but denorms in FailingTriggers models by default
failingdenorms = denorms.get_alldenorms()
denorms.alldenorms = [d for d in failingdenorms if d.model not in (models.FailingTriggersModelA, models.FailingTriggersModelB)]


class TestTriggers(TestCase):
    def setUp(self):
        denorms.drop_triggers()

    def test_triggers(self):
        """Test potentially failing denorms.
        """
        # save and restore alldenorms
        # test will fail if it's raising an exception
        alldenorms = denorms.get_alldenorms()
        denorms.alldenorms = failingdenorms
        try:
            denorms.install_triggers()
        finally:
            denorms.alldenorms = alldenorms


class TestCached(TestCase):
    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

    def tearDown(self):
        models.CachedModelA.objects.all().delete()
        models.CachedModelB.objects.all().delete()

    def test_depends_related(self):
        models.CachedModelB.objects.create(data='Hello')
        b = models.CachedModelB.objects.all()[0]
        self.assertEqual('Hello', b.data)

        models.CachedModelA.objects.create(b=b)
        a = models.CachedModelA.objects.all()[0]

        self.assertEqual("HELLO", a.cached_data['upper'])
        self.assertEqual("hello", a.cached_data['lower'])

        b.data = 'World'
        self.assertEqual("HELLO", a.cached_data['upper'])
        self.assertEqual("hello", a.cached_data['lower'])

        b.save()
        a = models.CachedModelA.objects.all()[0]
        self.assertEqual("WORLD", a.cached_data['upper'])
        self.assertEqual("world", a.cached_data['lower'])


class TestAbstract(TestCase):
    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

    def test_abstract(self):
        d1 = models.RealDenormModel.objects.create(text='onion')
        self.assertEqual("Ham and onion", d1.ham)
        self.assertEqual("Eggs and onion", d1.eggs)


class TestSkip(TransactionTestCase):
    """
    Tests for the skip feature.
    """

    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

        post = models.SkipPost(text='Here be ponies.')
        post.save()

        self.post = post

    # TODO: Enable and check!
    # Unsure on how to test this behaviour. It results in an endless loop:
    # update -> trigger -> update -> trigger -> ...
    #
    #def test_without_skip(self):
    #    # This results in an infinate loop on SQLite.
    #    comment = SkipCommentWithoutSkip(post=self.post, text='Oh really?')
    #    comment.save()
    #
    #    denorm.flush()

    # TODO: Check if an infinate loop happens and stop it.
    def test_with_skip(self):
        # This should not result in an endless loop.
        comment = models.SkipCommentWithSkip(post=self.post, text='Oh really?')
        comment.save()

        denorm.flush()

    def test_meta_skip(self):
        """Test a model with the attribute listed under denorm_always_skip."""
        comment = models.SkipCommentWithAttributeSkip(post=self.post, text='Yup, and they have wings!')
        comment.save()

        denorm.flush()


class TestDenormalisation(TransactionTestCase):
    """
    Tests for the denormalisation fields.
    """

    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

        self.testuser = User.objects.create_user("testuser", "testuser", "testuser")
        self.testuser.is_staff = True
        ctype = ContentType.objects.get_for_model(models.Member)
        self.testuser.save()

    def tearDown(self):
        # delete all model instances
        self.testuser.delete()
        models.Attachment.objects.all().delete()
        models.Post.objects.all().delete()
        models.Forum.objects.all().delete()

    def test_depends_related(self):
        """
        Test the DependsOnRelated stuff.
        """
        # Make a forum, check it's got no posts
        f1 = models.Forum.objects.create(title="forumone")
        self.assertEqual(f1.post_count, 0)
        # Check its database copy too
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 0)

        # Add a post
        p1 = models.Post.objects.create(forum=f1)
        # Has the post count updated?
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 1)

        denorm.flush()

        # Check its title, in p1 and the DB
        self.assertEqual(p1.forum_title, "forumone")
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title, "forumone")

        # Update the forum title
        f1.title = "forumtwo"
        f1.save()

        denorm.flush()

        # Has the post's title changed?
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title, "forumtwo")

        # Add and remove some posts and check the post count
        models.Post.objects.create(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 2)
        models.Post.objects.create(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 3)
        p1.delete()
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 2)

        # Delete everything, check once more.
        models.Post.objects.all().delete()
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 0)

        # Make an orphaned post, see what its title is.
        # Doesn't work yet - no support for null FKs
        #p4 = Post.objects.create(forum=None)
        #self.assertEqual(p4.forum_title, None)

    def test_dependency_chains(self):
        # create a forum, a member and a post
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        models.Post.objects.create(forum=f1, author=m1)
        denorm.flush()

        # check the forums author list contains the member
        self.assertEqual(models.Forum.objects.get(id=f1.id).author_names, "memberone")

        # change the member's name
        m1.name = "membertwo"
        m1.save()
        denorm.flush()

        # check again
        self.assertEqual(models.Forum.objects.get(id=f1.id).author_names, "membertwo")

    def test_trees(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo", parent_forum=f1)
        f3 = models.Forum.objects.create(title="forumthree", parent_forum=f2)
        denorm.flush()

        self.assertEqual(f1.path, '/forumone/')
        self.assertEqual(f2.path, '/forumone/forumtwo/')
        self.assertEqual(f3.path, '/forumone/forumtwo/forumthree/')

        f1.title = 'someothertitle'
        f1.save()
        denorm.flush()

        f1 = models.Forum.objects.get(id=f1.id)
        f2 = models.Forum.objects.get(id=f2.id)
        f3 = models.Forum.objects.get(id=f3.id)

        self.assertEqual(f1.path, '/someothertitle/')
        self.assertEqual(f2.path, '/someothertitle/forumtwo/')
        self.assertEqual(f3.path, '/someothertitle/forumtwo/forumthree/')

    def test_reverse_fk_null(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        models.Post.objects.create(forum=f1, author=m1)
        models.Attachment.objects.create()
        denorm.flush()

    def test_bulk_update(self):
        """
        Test the DependsOnRelated stuff.
        """
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo")
        p1 = models.Post.objects.create(forum=f1)
        p2 = models.Post.objects.create(forum=f2)
        denorm.flush()

        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title, "forumone")
        self.assertEqual(models.Post.objects.get(id=p2.id).forum_title, "forumtwo")
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 1)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count, 1)

        models.Post.objects.update(forum=f1)
        denorm.flush()
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title, "forumone")
        self.assertEqual(models.Post.objects.get(id=p2.id).forum_title, "forumone")
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 2)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count, 0)

        models.Forum.objects.update(title="oneforall")
        denorm.flush()
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title, "oneforall")
        self.assertEqual(models.Post.objects.get(id=p2.id).forum_title, "oneforall")

    def test_no_dependency(self):
        m1 = models.Member.objects.create(first_name="first", name="last")
        denorm.flush()

        self.assertEqual(models.Member.objects.get(id=m1.id).full_name, "first last")

        models.Member.objects.filter(id=m1.id).update(first_name="second")
        denorm.flush()
        self.assertEqual(models.Member.objects.get(id=m1.id).full_name, "second last")

    def test_self_backward_relation(self):

        f1 = models.Forum.objects.create(title="forumone")
        p1 = models.Post.objects.create(forum=f1, )
        p2 = models.Post.objects.create(forum=f1, response_to=p1)
        p3 = models.Post.objects.create(forum=f1, response_to=p1)
        p4 = models.Post.objects.create(forum=f1, response_to=p2)
        denorm.flush()

        self.assertEqual(models.Post.objects.get(id=p1.id).response_count, 3)
        self.assertEqual(models.Post.objects.get(id=p2.id).response_count, 1)
        self.assertEqual(models.Post.objects.get(id=p3.id).response_count, 0)
        self.assertEqual(models.Post.objects.get(id=p4.id).response_count, 0)

    def test_m2m_relation(self):
        f1 = models.Forum.objects.create(title="forumone")
        p1 = models.Post.objects.create(forum=f1, title="post1")
        m1 = models.Member.objects.create(first_name="first1", name="last1")

        denorm.flush()
        m1.bookmarks.add(p1)
        denorm.flush()

        self.assertTrue('post1' in models.Member.objects.get(id=m1.id).bookmark_titles)
        p1.title = "othertitle"
        p1.save()
        denorm.flush()
        self.assertTrue('post1' not in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('othertitle' in models.Member.objects.get(id=m1.id).bookmark_titles)

        p2 = models.Post.objects.create(forum=f1, title="thirdtitle")
        m1.bookmarks.add(p2)
        denorm.flush()
        self.assertTrue('post1' not in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('othertitle' in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('thirdtitle' in models.Member.objects.get(id=m1.id).bookmark_titles)

        m1.bookmarks.remove(p1)
        denorm.flush()
        self.assertTrue('othertitle' not in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('thirdtitle' in models.Member.objects.get(id=m1.id).bookmark_titles)

    def test_middleware(self):
        # FIXME, this test currently does not work with a transactional
        # database, so it's skipped for now.
        return
        # FIXME, set and de-set middleware values
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(first_name="first1", name="last1")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        self.assertEqual(models.Post.objects.get(id=p1.id).author_name, "last1")

        self.client.login(username="testuser", password="testuser")
        self.client.post("/admin/denorm_testapp/member/%s/" % (m1.pk), {
            'name': 'last2',
            'first_name': 'first2',
        })

        self.assertEqual(models.Post.objects.get(id=p1.id).author_name, "last2")

    def test_countfield(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumone")
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 0)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count, 0)

        models.Post.objects.create(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 1)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count, 0)

        p2 = models.Post.objects.create(forum=f2)
        p3 = models.Post.objects.create(forum=f2)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 1)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count, 2)

        p2.forum = f1
        p2.save()
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 2)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count, 1)

        models.Post.objects.filter(pk=p3.pk).update(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 3)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count, 0)

    def test_countfield_does_not_write_stale_value(self):
        f1 = models.Forum.objects.create(title="forumone")
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 0)
        models.Post.objects.create(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 1)

        f1 = models.Forum.objects.get(title="forumone")
        models.Post.objects.create(forum_id=f1.id)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 2)
        f1.title = "new"
        self.assertEqual(f1.post_count, 1)
        f1.save()
        self.assertEqual(f1.post_count, 2)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count, 2)
        self.assertEqual(models.Forum.objects.get(id=f1.id).title, "new")

    def test_foreignkey(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo")
        m1 = models.Member.objects.create(first_name="first1", name="last1")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        a1 = models.Attachment.objects.create(post=p1)
        self.assertEqual(models.Attachment.objects.get(id=a1.id).forum, f1)

        a2 = models.Attachment.objects.create()
        self.assertEqual(models.Attachment.objects.get(id=a2.id).forum, None)

        # Change forum
        p1.forum = f2
        p1.save()
        denorm.flush()
        self.assertEqual(models.Attachment.objects.get(id=a1.id).forum, f2)

        # test denorm function returning object, not PK
        models.Attachment.forum_as_object = True
        a3 = models.Attachment.objects.create(post=p1)
        models.Attachment.forum_as_object = False

    def test_m2m(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        models.Post.objects.create(forum=f1, author=m1)
        denorm.flush()

        # check the forums author list contains the member
        self.assertTrue(m1 in models.Forum.objects.get(id=f1.id).authors.all())

        m2 = models.Member.objects.create(name="membertwo")
        p2 = models.Post.objects.create(forum=f1, author=m2)
        denorm.flush()

        self.assertTrue(m1 in models.Forum.objects.get(id=f1.id).authors.all())
        self.assertTrue(m2 in models.Forum.objects.get(id=f1.id).authors.all())

        p2.delete()
        denorm.flush()

        self.assertTrue(m2 not in models.Forum.objects.get(id=f1.id).authors.all())

    def test_denorm_rebuild(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        denorm.denorms.rebuildall()

        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.post_count, 1)
        self.assertEqual(f1.authors.all()[0], m1)

    def test_denorm_rebuild_called_once(self):
        """
        Test whether the denorm function is not called only once during rebuild.
        The proxy model CallCounterProxy should not add extra callings to denorm function.
        """
        models.CallCounter.objects.create()
        denorm.denorms.flush()
        c = models.CallCounter.objects.get()
        self.assertEqual(c.called_count, 2)  # TODO: we should be able to create object with hitting the denorm function just once
        denorm.denorms.rebuildall(verbose=True)
        c = models.CallCounter.objects.get()
        self.assertEqual(c.called_count, 3)
        denorm.denorms.rebuildall(verbose=True)
        c = models.CallCounter.objects.get()
        self.assertEqual(c.called_count, 4)

    def test_denorm_update(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(forum=f1, author=m1)
        a1 = models.Attachment.objects.create(post=p1)

        denorm.denorms.rebuildall()

        f2 = models.Forum.objects.create(title="forumtwo")
        p1.forum = f2
        p1.save()

        # BUG https://github.com/initcrash/django-denorm/issues/24
        # We have to update the Attachment.forum field first to trigger this bug. Simply doing rebuildall() will
        # trigger an a1.save() at an some earlier point during the update. By the time we get to updating the value of
        # forum field the value is already correct and no update is done bypassing the broken code.
        denorm.denorms.rebuildall(model_name='Attachment', field_name='forum')

    def test_denorm_subclass(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        self.assertEqual(f1.tags_string, '')
        self.assertEqual(p1.tags_string, '')

        models.Tag.objects.create(name='tagone', content_object=f1)
        models.Tag.objects.create(name='tagtwo', content_object=f1)

        denorm.denorms.flush()
        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.tags_string, 'tagone, tagtwo')
        self.assertEqual(p1.tags_string, '')

        models.Tag.objects.create(name='tagthree', content_object=p1)
        t4 = models.Tag.objects.create(name='tagfour', content_object=p1)

        denorm.denorms.flush()
        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.tags_string, 'tagone, tagtwo')
        self.assertEqual(p1.tags_string, 'tagfour, tagthree')

        t4.content_object = f1
        t4.save()

        denorm.denorms.flush()
        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.tags_string, 'tagfour, tagone, tagtwo')
        self.assertEqual(p1.tags_string, 'tagthree')

    def test_cache_key_field_backward(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo")
        ck1 = f1.cachekey
        ck2 = f2.cachekey

        p1 = models.Post.objects.create(forum=f1)
        f1 = models.Forum.objects.get(id=f1.id)
        f2 = models.Forum.objects.get(id=f2.id)
        self.assertNotEqual(ck1, f1.cachekey)
        self.assertEqual(ck2, f2.cachekey)

        ck1 = f1.cachekey
        ck2 = f2.cachekey

        p1 = models.Post.objects.get(id=p1.id)
        p1.forum = f2
        p1.save()

        f1 = models.Forum.objects.get(id=f1.id)
        f2 = models.Forum.objects.get(id=f2.id)

        self.assertNotEqual(ck1, f1.cachekey)
        self.assertNotEqual(ck2, f2.cachekey)

    def test_cache_key_field_forward(self):
        f1 = models.Forum.objects.create(title="forumone")
        p1 = models.Post.objects.create(title='initial_title', forum=f1)
        a1 = models.Attachment.objects.create(post=p1)
        a2 = models.Attachment.objects.create(post=p1)

        a1 = models.Attachment.objects.get(id=a1.id)
        a2 = models.Attachment.objects.get(id=a2.id)
        self.assertNotEqual(a1.cachekey, a2.cachekey)

        ck1 = a1.cachekey
        ck2 = a2.cachekey
        p1.title = 'new_title'
        p1.save()

        a1 = models.Attachment.objects.get(id=a1.id)
        a2 = models.Attachment.objects.get(id=a2.id)
        self.assertNotEqual(ck1, a1.cachekey)
        self.assertNotEqual(ck2, a2.cachekey)

        a1 = models.Attachment.objects.get(id=a1.id)
        a2 = models.Attachment.objects.get(id=a2.id)
        self.assertNotEqual(a1.cachekey, a2.cachekey)

    def test_cache_key_field_m2m(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(title='initial_title', forum=f1)

        m1 = models.Member.objects.get(id=m1.id)
        ck1 = m1.cachekey

        m1.bookmarks.add(p1)

        m1 = models.Member.objects.get(id=m1.id)
        self.assertNotEqual(ck1, m1.cachekey)

        ck1 = m1.cachekey

        p1 = models.Post.objects.get(id=p1.id)
        p1.title = 'new_title'
        p1.save()

        m1 = models.Member.objects.get(id=m1.id)
        self.assertNotEqual(ck1, m1.cachekey)


class DeletionTestCase(TestCase):
    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

    def test_deletion_triggers_update(self):
        bar = models.Bar.objects.create()
        self.assertEqual(0, bar.value)
        foo = models.Foo.objects.create(bar=bar)

        denorm.flush()

        bar = models.Bar.objects.get(pk=bar.pk)
        self.assertEqual(1, bar.value)

        foo.delete()

        denorm.flush()

        bar = models.Bar.objects.get(pk=bar.pk)
        self.assertEqual(0, bar.value)


if connection.vendor != "sqlite":
    class TestFilterCount(TestCase):
        """
        Tests for the filtered count feature.
        """
        def setUp(self):
            denorms.drop_triggers()
            denorms.install_triggers()

        def test_filter_count(self):
            master = models.FilterCountModel.objects.create()
            self.assertEqual(master.active_item_count, 0)
            master.items.create(active=True, text='text')
            master.items.create(active=True, text='')
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count, 1, 'created active item')
            master.items.create(active=False)
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count, 1, 'created inactive item')
            master.items.create(active=True, text='true')
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 2)
            master.items.filter(active=False).delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 2)
            master.items.filter(active=True, text='true')[0].delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 1)
            item = master.items.filter(active=True, text='text')[0]
            item.active = False
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 0)
            item = master.items.filter(active=False, text='text')[0]
            item.active = True
            item.text = ''
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 0)
            item = master.items.filter(active=True, text='')[0]
            item.text = '123'
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 1)

    class TestFilterCountM2M(TestCase):
        """
        Tests for the filtered count feature.
        """
        def setUp(self):
            denorms.drop_triggers()
            denorms.install_triggers()

        def test_filter_count(self):
            master = models.FilterCountModel.objects.create()
            self.assertEqual(master.active_item_count, 0)
            master.items.create(active=True, text='true')
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count, 1, 'created active item')
            master.items.create(active=False, text='true')
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count, 1, 'created inactive item')
            master.items.create(active=True, text='true')
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 2)
            master.items.filter(active=False).delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 2)
            master.items.filter(active=True)[0].delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 1)
            item = master.items.filter(active=True)[0]
            item.active = False
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 0)
            item = master.items.filter(active=False)[0]
            item.active = True
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count, 1)

    class TestFilterSum(TestCase):
        """
        Tests for the filtered count feature.
        """

        def setUp(self):
            denorms.drop_triggers()
            denorms.install_triggers()

        def test_filter_count(self):
            master = models.FilterSumModel.objects.create()
            self.assertEqual(master.active_item_sum, 0)
            master.counts.create(age=18, active_item_count=8)
            master = models.FilterSumModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_sum, 8)
            master.counts.create(age=16, active_item_count=10)
            master = models.FilterSumModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_sum, 8, 'created inactive item')
            master.counts.create(age=19, active_item_count=9)
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum, 17)
            master.counts.filter(age__lt=18).delete()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum, 17)
            master.counts.filter(age=19)[0].delete()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum, 8)
            item = master.counts.filter(age=18)[0]
            item.age = 15
            item.save()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum, 0)
            item = master.counts.filter(age=15)[0]
            item.age = 18
            item.save()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum, 8)


class CommandsTestCase(TransactionTestCase):
    def test_denorm_daemon(self):
        " Test denorm_daemon command."

        call_command('denorm_daemon', run_once=True, foreground=True)

    if Decimal('.'.join([str(i) for i in django.VERSION[:2]])) >= Decimal('1.7'):
        def test_makemigrations(self):
            " Test makemigrations command."

            args = []
            opts = {}
            call_command('makemigrations', *args, **opts)
