# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from denorm.db import triggers
from django.db.models.manager import Manager
from denorm.models import DirtyInstance

# remember all denormalizations.
# this is used to rebuild all denormalized values in the whole DB
alldenorms = []


def many_to_many_pre_save(sender, instance, **kwargs):
    """
    Updates denormalised many-to-many fields for the model
    """
    if instance.pk:
        # need a primary key to do m2m stuff
        for m2m in sender._meta.local_many_to_many:
            # This gets us all m2m fields, so limit it to just those that are denormed
            if hasattr(m2m, "denorm"):
                # Does some extra jiggery-pokery for "through" m2m models.
                # May not work under lots of conditions.
                if hasattr(m2m.rel, 'through_model'):

                    # Clear exisiting through records (bit heavy handed?)
                    kwargs = { m2m.related.var_name: instance, }

                    # Can't use m2m_column_name in a filter
                    # kwargs = { m2m.m2m_column_name(): instance.pk, }
                    m2m.rel.through_model.objects.filter(**kwargs).delete()

                    values = m2m.denorm.func(instance)
                    for value in values:
                        kwargs.update({m2m.m2m_reverse_name(): value.pk,})
                        m2m.rel.through_model.objects.create(**kwargs)

                else:
                    values = m2m.denorm.func(instance)
                    setattr(instance, m2m.attname, values)

def many_to_many_post_save(sender, instance, created, **kwargs):
    if created:
        def check_resave():
            for m2m in sender._meta.local_many_to_many:
                if hasattr(m2m, "denorm"):
                    return True
            return False

        if check_resave():
            instance.save()

class Denorm(object):

    def __init__(self, skip=None):
        self.func = None
        self.skip = skip

    def setup(self,**kwargs):
        """
        Adds 'self' to the global denorm list
        and connects all needed signals.
        """
        global alldenorms
        if self not in alldenorms:
            alldenorms.append(self)

    def update(self,qs):
        """
        Updates the denormalizations in all instances in the queryset 'qs'.
        """
        for instance in qs.distinct():
            # only write new values to the DB if they actually changed
            new_value = self.func(instance)

            # Get attribute name (required for denormalising ForeignKeys)
            attname = instance._meta.get_field(self.fieldname).attname

            if isinstance(getattr(instance,attname), Manager) and getattr(instance,attname).all() != new_value:
                # many to many field
                for o in qs.filter(pk=instance.pk):
                    o.attname = new_value
                instance.save()

            elif not getattr(instance,attname) == new_value:
                setattr(instance,attname,new_value)
                # an update before the save is needed to handle CountFields
                # CountField does not update its value during pre_save
                qs.filter(pk=instance.pk).update(**{attname:new_value})
                instance.save()
        flush()

    def get_triggers(self, using):
        return []

class BaseCallbackDenorm(Denorm):
    """
    Handles the denormalization of one field, using a python function
    as a callback.
    """

    def setup(self,**kwargs):
        """
        Calls setup() on all DenormDependency resolvers
        """
        super(BaseCallbackDenorm,self).setup(**kwargs)

        for dependency in self.depend:
            dependency.setup(self.model)

    def get_triggers(self, using):
        """
        Creates a list of all triggers needed to keep track of changes
        to fields this denorm depends on.
        """
        trigger_list = list()

        # Get the triggers of all DenormDependency instances attached
        # to our callback.
        for dependency in self.depend:
            trigger_list += dependency.get_triggers(using=using)

        return trigger_list + super(BaseCallbackDenorm,self).get_triggers(using=using)

class CallbackDenorm(BaseCallbackDenorm):
    """
    As above, but with extra triggers on self as described below
    """

    def get_triggers(self, using):

        content_type = str(ContentType.objects.get_for_model(self.model).pk)

        # Create a trigger that marks any updated or newly created
        # instance of the model containing the denormalized field
        # as dirty.
        # This is only really needed if the instance was changed without
        # using the ORM or if it was part of a bulk update.
        # In those cases the self_save_handler won't get called by the
        # pre_save signal, so we need to ensure flush() does this later.
        action = triggers.TriggerActionInsert(
            model = DirtyInstance,
            columns = ("content_type_id","object_id"),
            values = (content_type,"NEW.%s" % self.model._meta.pk.get_attname_column()[1])
        )
        trigger_list = [
            triggers.Trigger(self.model,"after","update",[action],content_type,using,self.skip),
            triggers.Trigger(self.model,"after","insert",[action],content_type,using,self.skip),
        ]

        return trigger_list + super(CallbackDenorm,self).get_triggers(using=using)

class BaseCacheKeyDenorm(Denorm):
    def __init__(self,depend_on_related,*args,**kwargs):
        self.depend = depend_on_related
        super(BaseCacheKeyDenorm,self).__init__(*args,**kwargs)
        import random
        self.func = lambda o: random.randint(-9223372036854775808,9223372036854775807)

    def setup(self,**kwargs):
        """
        Calls setup() on all DenormDependency resolvers
        """
        super(BaseCacheKeyDenorm,self).setup(**kwargs)

        for dependency in self.depend:
            dependency.setup(self.model)

    def get_triggers(self,using):
        """
        Creates a list of all triggers needed to keep track of changes
        to fields this denorm depends on.
        """
        trigger_list = list()

        # Get the triggers of all DenormDependency instances attached
        # to our callback.
        for dependency in self.depend:
            trigger_list += dependency.get_triggers(using=using)

        return trigger_list + super(BaseCacheKeyDenorm,self).get_triggers(using=using)

class CacheKeyDenorm(BaseCacheKeyDenorm):
    """
    As above, but with extra triggers on self as described below
    """

    def get_triggers(self, using):

        content_type = str(ContentType.objects.get_for_model(self.model).pk)

        # This is only really needed if the instance was changed without
        # using the ORM or if it was part of a bulk update.
        # In those cases the self_save_handler won't get called by the
        # pre_save signal
        action = triggers.TriggerActionUpdate(
            model = self.model,
            columns = (self.fieldname,),
            values = (triggers.RandomBigInt(),),
            where = "%s=NEW.%s"%((self.model._meta.pk.get_attname_column()[1],)*2),
        )
        trigger_list = [
            triggers.Trigger(self.model,"after","update",[action],content_type,using,self.skip),
            triggers.Trigger(self.model,"after","insert",[action],content_type,using,self.skip),
        ]

        return trigger_list + super(CacheKeyDenorm,self).get_triggers(using=using)


class CountDenorm(Denorm):

    """
    Handles the denormalization of a count field by doing incrementally
    updates.
    """

    def __init__(self, skip=None):
        # in case we want to set the value without relying on the
        # correctness of the incremental updates we create a function that
        # calculates it from scratch.
        self.func = lambda obj: getattr(obj,self.manager_name).count()
        self.manager = None
        self.skip = skip

    def setup(self,sender,**kwargs):
        # as we connected to the ``class_prepared`` signal for any sender
        # and we only need to setup once, check if the sender is our model.
        if sender is self.model:
            super(CountDenorm,self).setup(sender=sender,**kwargs)

        # related managers will only by available after both models are initialized
        # so check if its available already, and get our manager
        if not self.manager and hasattr(self.model,self.manager_name):
            self.manager = getattr(self.model,self.manager_name)

    def get_triggers(self, using):
        fk_name = self.manager.related.field.attname
        content_type = str(ContentType.objects.get_for_model(self.model).pk)

        # create the triggers for the incremental updates
        increment = triggers.TriggerActionUpdate(
            model = self.model,
            columns = (self.fieldname,),
            values = ("%s+1" % self.fieldname,),
            where = "%s=NEW.%s" % (self.model._meta.pk.get_attname_column()[1], fk_name),
        )
        decrement = triggers.TriggerActionUpdate(
            model = self.model,
            columns = (self.fieldname,),
            values = ("%s-1" % self.fieldname,),
            where = "%s=OLD.%s" % (self.model._meta.pk.get_attname_column()[1], fk_name),
        )

        other_model = self.manager.related.model
        return [
            triggers.Trigger(other_model,"after","update",[increment,decrement],content_type,using,self.skip),
            triggers.Trigger(other_model,"after","insert",[increment],content_type,using,self.skip),
            triggers.Trigger(other_model,"after","delete",[decrement],content_type,using,self.skip),
        ]

def rebuildall(verbose=False):
    """
    Updates all models containing denormalized fields.
    Used by the 'denormalize' management command.
    """
    global alldenorms
    for i,denorm in enumerate(alldenorms):
        if verbose:
            print 'rebuilding','%s/%s'%(i+1,len(alldenorms)),denorm.fieldname,'in',denorm.model
        denorm.update(denorm.model.objects.all())

def drop_triggers(using=None):
    triggerset = triggers.TriggerSet(using=using)
    triggerset.drop()

def install_triggers(using=None):
    """
    Installs all required triggers in the database
    """
    build_triggerset(using=using).install()

def build_triggerset(using=None):
    global alldenorms

    # Use a TriggerSet to ensure each event gets just one trigger
    triggerset = triggers.TriggerSet(using=using)
    for denorm in alldenorms:
        triggerset.append(denorm.get_triggers(using=using))
    return triggerset

def flush():
    """
    Updates all model instances marked as dirty by the DirtyInstance
    model.
    After this method finishes the DirtyInstance table is empty and
    all denormalized fields have consistent data.
    """

    # Loop until break.
    # We may need multiple passes, because an update on one instance
    # may cause an other instance to be marked dirty (dependency chains)
    while True:
        # Get all dirty markers
        qs = DirtyInstance.objects.all()

        # DirtyInstance table is empty -> all data is consistent -> we're done
        if not qs: break

        # Call save() on all dirty instances, causing the self_save_handler()
        # getting called by the pre_save signal.
        for dirty_instance in qs:
            if dirty_instance.content_object:
                dirty_instance.content_object.save()
            dirty_instance.delete()

