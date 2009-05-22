# -*- coding: utf-8 -*-
from denorm.helpers import find_fks,find_m2ms
from django.db.models.fields import related
from denorm.models import DirtyInstance
from django.contrib.contenttypes.models import ContentType
from denorm.db import triggers

def make_depend_decorator(Resolver):
    def decorator(*args,**kwargs):
        def deco(func):
            if not hasattr(func,'depend'):
                func.depend = []
            func.depend += [Resolver(*args,**kwargs)]
            return func
        return deco
    return decorator

class DenormDependency:
    def resolve(*args,**kwargs):
        return None
    def setup(*args,**kwargs):
        pass

class DependOnRelated(DenormDependency):
    def __init__(self,model,foreign_key=None,type=None):
        self.other_model = model
        self.foreign_key = foreign_key
        self.type = type

    def get_triggers(self):
        content_type = str(ContentType.objects.get_for_model(self.this_model).id)

        if self.type == "forward":
            update_trigger = triggers.Trigger(self.other_model,"after","update")
            insert_trigger = triggers.Trigger(self.other_model,"after","insert")
            delete_trigger = triggers.Trigger(self.other_model,"after","delete")
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,"id"),
                    **{self.foreign_key+"_id":"NEW.id"}
                )
            )
            action_old = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,"id"),
                    **{self.foreign_key+"_id":"OLD.id"}
                )
            )
            update_trigger.append(action_new)
            insert_trigger.append(action_new)
            delete_trigger.append(action_old)
            return [update_trigger,insert_trigger,delete_trigger]

        if self.type == "backward":
            update_trigger = triggers.Trigger(self.other_model,"after","update")
            insert_trigger = triggers.Trigger(self.other_model,"after","insert")
            delete_trigger = triggers.Trigger(self.other_model,"after","delete")
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "NEW.%s_id" % self.foreign_key,
                )
            )
            action_old = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "OLD.%s_id" % self.foreign_key,
                )
            )
            update_trigger.append([action_new,action_old])
            insert_trigger.append(action_new)
            delete_trigger.append(action_old)
            return [update_trigger,insert_trigger,delete_trigger]

        if "m2m" in self.type:
            if "forward" in self.type:
                column_name = self.field.m2m_column_name()
                reverse_column_name = self.field.m2m_reverse_name()
            if "backward" in self.type:
                column_name = self.field.m2m_reverse_name()
                reverse_column_name = self.field.m2m_column_name()

            m2m_update_trigger = triggers.Trigger(self.field,"after","update")
            m2m_insert_trigger = triggers.Trigger(self.field,"after","insert")
            m2m_delete_trigger = triggers.Trigger(self.field,"after","delete")
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "NEW.%s" % column_name,
                )
            )
            action_old = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = (
                    content_type,
                    "OLD.%s" % column_name,
                )
            )
            m2m_update_trigger.append([action_new,action_old])
            m2m_insert_trigger.append(action_new)
            m2m_delete_trigger.append(action_old)

            update_trigger = triggers.Trigger(self.other_model,"after","update")
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.field.m2m_db_table(),
                    (content_type,column_name),
                    **{reverse_column_name:"NEW.id"}
                )
            )
            update_trigger.append(action_new)

            return [update_trigger,m2m_update_trigger,m2m_insert_trigger,m2m_delete_trigger]

        return []


    def setup(self,this_model, **kwargs):
        self.this_model = this_model

        # FIXME: this should not be necessary
        if self.other_model == related.RECURSIVE_RELATIONSHIP_CONSTANT:
            self.other_model = self.this_model

        if isinstance(self.other_model,(str,unicode)):
            related.add_lazy_relation(self.this_model, None, self.other_model, self.resolved_model)
        else:
            self.resolved_model(None,self.other_model,None)

    def resolved_model(self, data, model, cls):
        self.other_model = model

        candidates =  [('forward',fk) for fk in find_fks(self.this_model,self.other_model,self.foreign_key)]
        candidates += [('backward',fk) for fk in find_fks(self.other_model,self.this_model,self.foreign_key)]
        candidates += [('forward_m2m',fk) for fk in find_m2ms(self.this_model,self.other_model,self.foreign_key)]
        candidates += [('backward_m2m',fk) for fk in find_m2ms(self.other_model,self.this_model,self.foreign_key)]

        if self.type:
            candidates = [x for x in candidates if self.type == x[0]]

        if len(candidates) > 1:
            raise ValueError("%s has more than one ForeignKey or ManyToManyField to %s (or reverse); cannot auto-resolve."
                             % (self.this_model, self.other_model))
        if not candidates:
            raise ValueError("%s has no ForeignKeys or ManyToManyFields to %s (or reverse); cannot auto-resolve."
                             % (self.this_model, self.other_model))

        winner = candidates[0]
        self.type = winner[0]
        self.foreign_key = winner[1].attname
        self.field = winner[1]

        if self.type in ('forward','backward') and self.foreign_key.endswith("_id"):
            self.foreign_key = self.foreign_key[:-3]


depend_on_related = make_depend_decorator(DependOnRelated)

