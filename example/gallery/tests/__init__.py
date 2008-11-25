"""
>>> from django.contrib.auth.models import User
>>> user1 = User(username='user1')
>>> user1.save()
>>> user2 = User(username='user2')
>>> user2.save()
>>> from gallery.models import *
>>> gallery1 = Gallery(name='Gallery1')
>>> gallery1.save()
>>> gallery2 = Gallery(name='Gallery2')
>>> gallery2.save()

>>> Picture(name='Picture1',gallery=gallery1,owner=user1,image='uploads/picture1.jpg').save()
>>> Gallery.objects.get(name='Gallery1').users
u'user1'
>>> Gallery.objects.get(name='Gallery2').users
u''

>>> Picture(name='Picture2',gallery=gallery2,owner=user2,image='uploads/picture2.jpg').save()
>>> Gallery.objects.get(name='Gallery1').users
u'user1'
>>> Gallery.objects.get(name='Gallery2').users
u'user2'

>>> pic = Picture.objects.get(name='Picture2')
>>> pic.gallery = gallery1
>>> pic.save()
>>> Gallery.objects.get(name='Gallery1').users
u'user1, user2'
>>> Gallery.objects.get(name='Gallery2').users
u''

>>> Picture.objects.get(name='Picture2').delete()
>>> Gallery.objects.get(name='Gallery1').users
u'user1'
>>> Gallery.objects.get(name='Gallery2').users
u''

>>> user = User.objects.get(username='user1')
>>> user.username = 'somenewname'
>>> user.save()
>>> Gallery.objects.get(name='Gallery1').users
u'somenewname'

"""
