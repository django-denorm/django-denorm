# -*- coding: utf-8 -*-
from denorm.helpers import find_fk
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
        update_trigger = triggers.Trigger(self.other_model,"after","update")
        insert_trigger = triggers.Trigger(self.other_model,"after","insert")
        delete_trigger = triggers.Trigger(self.other_model,"after","delete")
        content_type = str(ContentType.objects.get_for_model(self.this_model).id)

        if self.type == "forward":
            action_new = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.this_model,
                    (content_type,"id"),
                    **{self.foreign_key+"_id":"NEW.id"}
                )
            )
            action_old = triggers.TriggerActionInsert(
                model = DirtyInstance,
                columns = ("content_type_id","object_id"),
                values = triggers.TriggerNestedSelect(
                    self.this_model,
                    (content_type,"id"),
                    **{self.foreign_key+"_id":"OLD.id"}
                )
            )
            update_trigger.append(action_new)
            insert_trigger.append(action_new)
            delete_trigger.append(action_old)

        elif self.type == "backward":
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

        else:
            raise

        return [update_trigger,insert_trigger,delete_trigger]


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

        if self.type == 'forward' or not self.type:
            foreign_key = find_fk(self.this_model,self.other_model,self.foreign_key)
            if foreign_key:
                self.type = 'forward'
                self.foreign_key = foreign_key
                return

        if self.type == 'backward' or not self.type:
            self.foreign_key = find_fk(self.other_model,self.this_model,self.foreign_key)
            if self.foreign_key:
                self.type = 'backward'
                return

        raise ValueError("%s has no ForeignKeys to %s (or reverse); cannot auto-resolve."
                         % (self.this_model, self.other_model))
depend_on_related = make_depend_decorator(DependOnRelated)

