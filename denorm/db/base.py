from django.db import models, connections, connection
from django.contrib.contenttypes.generic import GenericRelation

class TriggerNestedSelect:
    def __init__(self,table,columns,**kwargs):
        self.table = table
        self.columns = ", ".join(columns)
        self.kwargs = kwargs

    def sql(self):
        raise NotImplementedError


class TriggerAction:
    def __init__(self):
        pass

    def sql(self):
        pass

class TriggerActionInsert(TriggerAction):
    def __init__(self,model,columns,values):
        self.model = model
        self.columns = columns
        self.values = values

    def sql(self):
        raise NotImplementedError

class TriggerActionUpdate(TriggerAction):
    def __init__(self,model,columns,values,where):
        self.model = model
        self.columns = columns
        self.values = values
        self.where = where

    def sql(self):
        raise NotImplementedError

class Trigger:

    def __init__(self, subject, time, event, actions, content_type, using=None, skip=None):
        self.subject = subject
        self.time = time
        self.event = event
        self.content_type = content_type
        self.content_type_field = None
        self.actions = []
        self.append(actions)
        self.using = using

        if self.using:
            cconnection = connections[self.using]
        else:
            cconnection = connection

        if isinstance(subject,models.ManyToManyField):
            self.model = None
            self.db_table = subject.m2m_db_table()
            self.fields = [(subject.m2m_column_name(), ''),(subject.m2m_reverse_name(),'')]
        elif isinstance(subject, GenericRelation):
            self.model = None
            self.db_table = subject.m2m_db_table()
            self.fields = [(k.attname, k.db_type(connection=cconnection)) for k, v in subject.rel.to._meta.get_fields_with_model() if not v]
            self.content_type_field = subject.content_type_field_name + '_id'
        elif hasattr(subject,"_meta"):
            self.model = subject
            self.db_table = self.model._meta.db_table
            # FIXME, need to check get_parent_list and add triggers to those
            # The below will only check the fields on *this* model, not parents
            skip = skip or ()
            self.fields = [(k.attname, k.db_type(connection=cconnection)) for k,v in self.model._meta.get_fields_with_model() if not v and k.attname not in skip]
        else:
            raise NotImplementedError

    def append(self,actions):
        if not isinstance(actions,list):
            actions = [actions]

        for action in actions:
            self.actions.append(action)

    def name(self):
        return "_".join([
            "denorm",
            self.time,
            "row",
            self.event,
            "on",
            self.db_table
        ])

    def sql(self):
        raise NotImplementedError

class TriggerSet:
    def __init__(self, using=None):
        self.using = using
        self.triggers = {}

    def cursor(self):
        if self.using:
            return connections[self.using].cursor()
        else:
            return connection.cursor()

    def append(self,triggers):
        if not isinstance(triggers,list):
            triggers = [triggers]

        for trigger in triggers:
            name = trigger.name()
            if self.triggers.has_key(name):
                self.triggers[name].append(trigger.actions)
            else:
                self.triggers[name] = trigger

    def install(self):
        raise NotImplementedError

    def drop(self):
        raise NotImplementedError
