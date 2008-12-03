import unittest
import datetime
import sys
import os

from django.core import management

# Add the tests directory so the denorm_testapp is on sys.path
test_root = os.path.dirname(__file__)
sys.path.append(test_root)

# Import denorm_testapp's models
import denorm_testapp.models
from denorm_testapp.models import *


class TestDenormalisation(unittest.TestCase):

    """
    Tests for the denormalisation fields.
    """
    
    def setUp(self):
        """Swaps out various Django calls for fake ones for our own nefarious purposes."""
        
        def new_get_apps():
            return [denorm_testapp.models]
        
        from django.db import models
        from django.conf import settings
        models.get_apps_old, models.get_apps = models.get_apps, new_get_apps
        settings.INSTALLED_APPS, settings.OLD_INSTALLED_APPS = (
            ["denorm_testapp"],
            settings.INSTALLED_APPS,
        )
        self.redo_app_cache()
        management.call_command('syncdb')
    
    
    def tearDown(self):
        """Undoes what monkeypatch did."""
        
        from django.db import models
        from django.conf import settings
        models.get_apps = models.get_apps_old
        settings.INSTALLED_APPS = settings.OLD_INSTALLED_APPS
        self.redo_app_cache()
        
        # Also delete all model instances
        Attachment.objects.all().delete()
        Post.objects.all().delete()
        Forum.objects.all().delete()
    
    
    def redo_app_cache(self):
        from django.db.models.loading import AppCache
        a = AppCache()
        a.loaded = False
        a._populate()
    
    
    def test_depends_related(self):
        """
        Test the DependsOnRelated stuff.
        """
        # Make a forum, check it's got no posts
        f1 = Forum.objects.create(title="forumone")
        self.assertEqual(f1.post_count, 0)
        # Check its database copy too
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 0)
        # Add a post
        p1 = Post.objects.create(forum=f1)
        # Check its title, in p1 and the DB
        self.assertEqual(p1.forum_title, "forumone")
        self.assertEqual(Post.objects.get(id=p1.id).forum_title, "forumone")
        # Has the post count updated?
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 1)
        # Update the forum title
        f1.title = "forumtwo"
        f1.save()
        # Has the post's title changed?
        self.assertEqual(Post.objects.get(id=p1.id).forum_title, "forumtwo")
        # Add and remove some posts
        p2 = Post.objects.create(forum=f1)
        p3 = Post.objects.create(forum=f1)
        p1.delete()
        # Check the post count
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 2)
        # Delete everything, check once more.
        Post.objects.all().delete()
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 0)
        # Make an orphaned post, see what its title is.
        # Doesn't work yet - no support for null FKs
        #p4 = Post.objects.create(forum=None)
        #self.assertEqual(p4.forum_title, None)

    def test_dependency_chains(self):
        # create a forum, a member and a post
        f1 = Forum.objects.create(title="forumone")
        m1 = Member.objects.create(name="memberone")
        p1 = Post.objects.create(forum=f1,author=m1)

        # check the forums author list contains the member
        self.assertEqual(Forum.objects.get(id=f1.id).authors, "memberone")

        # change the members name
        m1.name = "membertwo"
        m1.save()

        # check again
        self.assertEqual(Forum.objects.get(id=f1.id).authors, "membertwo")


