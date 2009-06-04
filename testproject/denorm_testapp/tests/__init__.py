import unittest
import datetime
import sys
import os

from django.core import management
from django.test import TestCase
from django.contrib.auth.models import User,Permission

# Add the tests directory so the denorm_testapp is on sys.path
test_root = os.path.dirname(__file__)
sys.path.append(test_root)

# Import denorm_testapp's models
import denorm_testapp.models
from denorm_testapp.models import *
from denorm.denorms import install_triggers
import denorm


class TestDenormalisation(TestCase):

    """
    Tests for the denormalisation fields.
    """

    def setUp(self):
        install_triggers()

        self.testuser = User.objects.create_user("testuser","testuser","testuser")
        self.testuser.is_staff = True
        Permission.objects.get(name='Can change member').user_set.add(self.testuser)
        self.testuser.save()

    def tearDown(self):
        # delete all model instances
        self.testuser.delete()
        Attachment.objects.all().delete()
        Post.objects.all().delete()
        Forum.objects.all().delete()

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
        # Has the post count updated?
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 1)

        denorm.flush()

        # Check its title, in p1 and the DB
        self.assertEqual(p1.forum_title, "forumone")
        self.assertEqual(Post.objects.get(id=p1.id).forum_title, "forumone")

        # Update the forum title
        f1.title = "forumtwo"
        f1.save()

        denorm.flush()

        # Has the post's title changed?
        self.assertEqual(Post.objects.get(id=p1.id).forum_title, "forumtwo")

        # Add and remove some posts and check the post count
        p2 = Post.objects.create(forum=f1)
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 2)
        p3 = Post.objects.create(forum=f1)
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 3)
        p1.delete()
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
        denorm.flush()

        # check the forums author list contains the member
        self.assertEqual(Forum.objects.get(id=f1.id).authors, "memberone")

        # change the members name
        m1.name = "membertwo"
        m1.save()
        denorm.flush()

        # check again
        self.assertEqual(Forum.objects.get(id=f1.id).authors, "membertwo")

    def test_trees(self):
        f1 = Forum.objects.create(title="forumone")
        f2 = Forum.objects.create(title="forumtwo",parent_forum=f1)
        f3 = Forum.objects.create(title="forumthree",parent_forum=f2)
        denorm.flush()

        self.assertEqual(f1.path,'/forumone/')
        self.assertEqual(f2.path,'/forumone/forumtwo/')
        self.assertEqual(f3.path,'/forumone/forumtwo/forumthree/')

        f1.title = 'someothertitle'
        f1.save()
        denorm.flush()

        f1 = Forum.objects.get(id=f1.id)
        f2 = Forum.objects.get(id=f2.id)
        f3 = Forum.objects.get(id=f3.id)

        self.assertEqual(f1.path,'/someothertitle/')
        self.assertEqual(f2.path,'/someothertitle/forumtwo/')
        self.assertEqual(f3.path,'/someothertitle/forumtwo/forumthree/')

    def test_reverse_fk_null(self):
        f1 = Forum.objects.create(title="forumone")
        m1 = Member.objects.create(name="memberone")
        p1 = Post.objects.create(forum=f1,author=m1)
        a1 = Attachment.objects.create()
        denorm.flush()


    def test_bulk_update(self):
        """
        Test the DependsOnRelated stuff.
        """
        f1 = Forum.objects.create(title="forumone")
        f2 = Forum.objects.create(title="forumtwo")
        p1 = Post.objects.create(forum=f1)
        p2 = Post.objects.create(forum=f2)
        denorm.flush()

        self.assertEqual(Post.objects.get(id=p1.id).forum_title, "forumone")
        self.assertEqual(Post.objects.get(id=p2.id).forum_title, "forumtwo")
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 1)
        self.assertEqual(Forum.objects.get(id=f2.id).post_count, 1)

        Post.objects.update(forum=f1)
        denorm.flush()
        self.assertEqual(Post.objects.get(id=p1.id).forum_title, "forumone")
        self.assertEqual(Post.objects.get(id=p2.id).forum_title, "forumone")
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 2)
        self.assertEqual(Forum.objects.get(id=f2.id).post_count, 0)

        Forum.objects.update(title="oneforall")
        denorm.flush()
        self.assertEqual(Post.objects.get(id=p1.id).forum_title, "oneforall")
        self.assertEqual(Post.objects.get(id=p2.id).forum_title, "oneforall")

    def test_no_dependency(self):
        m1 = Member.objects.create(first_name="first",name="last")
        denorm.flush()

        self.assertEqual(Member.objects.get(id=m1.id).full_name,"first last")

        Member.objects.filter(id=m1.id).update(first_name="second")
        denorm.flush()
        self.assertEqual(Member.objects.get(id=m1.id).full_name,"second last")

    def test_self_backward_relation(self):

        f1 = Forum.objects.create(title="forumone")
        p1 = Post.objects.create(forum=f1,)
        p2 = Post.objects.create(forum=f1,response_to=p1)
        p3 = Post.objects.create(forum=f1,response_to=p1)
        p4 = Post.objects.create(forum=f1,response_to=p2)
        denorm.flush()

        self.assertEqual(Post.objects.get(id=p1.id).response_count, 3)
        self.assertEqual(Post.objects.get(id=p2.id).response_count, 1)
        self.assertEqual(Post.objects.get(id=p3.id).response_count, 0)
        self.assertEqual(Post.objects.get(id=p4.id).response_count, 0)

    def test_m2m_relation(self):
        f1 = Forum.objects.create(title="forumone")
        p1 = Post.objects.create(forum=f1,title="post1")
        m1 = Member.objects.create(first_name="first1",name="last1")

        denorm.flush()
        m1.bookmarks.add(p1)
        denorm.flush()

        self.assertTrue('post1' in Member.objects.get(id=m1.id).bookmark_titles)
        p1.title = "othertitle"
        p1.save()
        denorm.flush()
        self.assertTrue('post1' not in Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('othertitle' in Member.objects.get(id=m1.id).bookmark_titles)

        p2 = Post.objects.create(forum=f1,title="thirdtitle")
        m1.bookmarks.add(p2)
        denorm.flush()
        self.assertTrue('post1' not in Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('othertitle' in Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('thirdtitle' in Member.objects.get(id=m1.id).bookmark_titles)

        m1.bookmarks.remove(p1)
        denorm.flush()
        self.assertTrue('othertitle' not in Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('thirdtitle' in Member.objects.get(id=m1.id).bookmark_titles)

    def test_middleware(self):
        f1 = Forum.objects.create(title="forumone")
        m1 = Member.objects.create(first_name="first1",name="last1")
        p1 = Post.objects.create(forum=f1,author=m1)

        self.assertEqual(Post.objects.get(id=p1.id).author_name, "last1")

        self.client.login(username="testuser",password="testuser")
        response = self.client.post("/admin/denorm_testapp/member/%s/"%(m1.pk),
                                {'name':'last2','first_name':'first2'})

        self.assertEqual(Post.objects.get(id=p1.id).author_name, "last2")

    def test_countfield(self):
        f1 = Forum.objects.create(title="forumone")
        f2 = Forum.objects.create(title="forumone")
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 0)
        self.assertEqual(Forum.objects.get(id=f2.id).post_count, 0)

        p1 = Post.objects.create(forum=f1)
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 1)
        self.assertEqual(Forum.objects.get(id=f2.id).post_count, 0)

        p2 = Post.objects.create(forum=f2)
        p3 = Post.objects.create(forum=f2)
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 1)
        self.assertEqual(Forum.objects.get(id=f2.id).post_count, 2)

        p2.forum = f1
        p2.save()
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 2)
        self.assertEqual(Forum.objects.get(id=f2.id).post_count, 1)

        Post.objects.filter(pk=p3.pk).update(forum=f1)
        self.assertEqual(Forum.objects.get(id=f1.id).post_count, 3)
        self.assertEqual(Forum.objects.get(id=f2.id).post_count, 0)
