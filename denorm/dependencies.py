# -*- coding: utf-8 -*-
from denorm.helpers import find_fk
from django.db.models.fields import related
from denorm.models import DirtyInstance
from django.contrib.contenttypes.models import ContentType

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
    def __init__(self,model,foreign_key=None):
        self.other_model = model
        self.foreign_key = foreign_key
        self.type = None


    def make_trigger(self,created_models,**kwargs):
        try:
            from django.db import connection
            cursor = connection.cursor()

            other_table = self.other_model._meta.db_table
            this_table = self.this_model._meta.db_table
            content_type = ContentType.objects.get_for_model(self.this_model).id
            dirty_table = DirtyInstance._meta.db_table
            triggername = "_".join(("trigger",other_table,))
            foreign_key = self.foreign_key
        except:
            pass

        try:
            cursor.execute("""DROP TRIGGER update_%s;""" % triggername)
        except:
            pass
        try:
            cursor.execute("""DROP TRIGGER insert_%s;""" % triggername)
        except:
            pass

        if self.type == "forward":
            sql = ["""
                CREATE TRIGGER update_%(triggername)s AFTER UPDATE ON %(other_table)s
                FOR EACH ROW BEGIN
                    INSERT INTO %(dirty_table)s (content_type_id, object_id, old_object_id)
                        (SELECT DISTINCT %(content_type)s,id,id FROM %(this_table)s
                            WHERE %(foreign_key)s_id = NEW.id);
                    INSERT INTO %(dirty_table)s (content_type_id, object_id, old_object_id)
                        (SELECT DISTINCT %(content_type)s,id,id FROM %(this_table)s
                            WHERE %(foreign_key)s_id = NEW.id);
                END
            """ % locals(),
            """
                CREATE TRIGGER insert_%(triggername)s AFTER INSERT ON %(other_table)s
                FOR EACH ROW
                    INSERT INTO %(dirty_table)s (content_type_id, object_id, old_object_id)
                        (SELECT DISTINCT %(content_type)s,id,id FROM %(this_table)s
                            WHERE %(foreign_key)s_id = NEW.id);
            """ % locals(),]

        try:
            if self.type == "backward":
                sql = ["""
                    CREATE TRIGGER update_%(triggername)s AFTER UPDATE ON %(other_table)s
                    FOR EACH ROW
                        INSERT INTO %(dirty_table)s (content_type_id, object_id, old_object_id)
                            VALUES (
                                %(content_type)s,
                                NEW.%(foreign_key)s_id,
                                OLD.%(foreign_key)s_id
                            );
                    CREATE TRIGGER insert_%(triggername)s AFTER INSERT ON %(other_table)s
                    FOR EACH ROW
                        INSERT INTO %(dirty_table)s (content_type_id, object_id, old_object_id)
                            VALUES (
                                %(content_type)s,
                                NEW.%(foreign_key)s_id,
                                NEW.%(foreign_key)s_id
                            );
                """ % locals(),]
        except:
            pass

        try:
            print "#####",other_table,this_table,self.type
            print "#####",triggername
            for q in sql:
                print q
                cursor.execute(q)
        except Exception, e:
            print Exception, e

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
        foreign_key = find_fk(self.this_model,self.other_model,self.foreign_key)
        if foreign_key:
            self.type = 'forward'
            self.foreign_key = foreign_key
            return
        self.foreign_key = find_fk(self.other_model,self.this_model,self.foreign_key)
        if self.foreign_key:
            self.type = 'backward'
            return
        raise ValueError("%s has no ForeignKeys to %s (or reverse); cannot auto-resolve."
                         % (self.this_model, self.other_model))
depend_on_related = make_depend_decorator(DependOnRelated)

