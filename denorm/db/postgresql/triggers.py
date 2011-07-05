from django.db import transaction
from denorm.db import base

class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.table
        where = ",".join(["%s = %s"%(k,v) for k,v in self.kwargs.iteritems()])
        return """ SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s """ % locals()

class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "("+",".join(self.columns)+")"
        if isinstance(self.values,TriggerNestedSelect):
            values = "("+self.values.sql()+")"
        else:
            values = "VALUES("+",".join(self.values)+")"

        return (
             """ BEGIN\n"""
            +"""     INSERT INTO %(table)s %(columns)s %(values)s;\n"""
            +"""    EXCEPTION WHEN unique_violation THEN\n     -- do nothing\n """
            +"""   END"""
            ) % locals()

class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        updates = ','.join(["%s=%s"%(k,v) for k,v in zip(self.columns,self.values)])
        where = self.where

        return """ UPDATE %(table)s SET %(updates)s WHERE %(where)s """ % locals()

class Trigger(base.Trigger):
    def name(self):
        name = base.Trigger.name(self)
        if self.content_type_field:
            name += "_%s" % self.content_type
        return name

    def sql(self):
        name = self.name()
        actions = (";\n   ").join(set([a.sql() for a in self.actions if a.sql()])) + ";"
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()
        content_type = self.content_type
        ct_field = self.content_type_field

        conditions = []

        if event == "UPDATE":
            for field, native_type in self.fields:
                if native_type is None:
                    # If Django didn't know what this field type should be
                    # then compare it as text - Fixes a problem of trying to
                    # compare PostGIS geometry fields.
                    conditions.append("(OLD.%(f)s::%(t)s IS DISTINCT FROM NEW.%(f)s::%(t)s)" % {'f': field, 't': 'text'})
                else:
                    conditions.append("( OLD.%(f)s IS DISTINCT FROM NEW.%(f)s )" % {'f': field,})

            conditions = ["(%s)"%"OR".join(conditions)]

        if ct_field:
            if event == "UPDATE":
                conditions.append("(OLD.%(ctf)s=%(ct)s)OR(NEW.%(ctf)s=%(ct)s)" % {'ctf': ct_field, 'ct': content_type})
            elif event == "INSERT":
                conditions.append("(NEW.%s=%s)" % (ct_field, content_type))
            elif event == "DELETE":
                conditions.append("(OLD.%s=%s)" % (ct_field, content_type))

        if not conditions:
            cond = "TRUE"
        else:
            cond = "AND".join(conditions)

        return (
             """ CREATE OR REPLACE FUNCTION func_%(name)s()\n"""
            +"""  RETURNS TRIGGER AS $$\n"""
            +"""  BEGIN\n"""
            +"""   IF %(cond)s THEN\n"""
            +"""    %(actions)s\n"""
            +"""   END IF;\n"""
            +"""  RETURN NULL; END;\n"""
            +"""  $$ LANGUAGE plpgsql;\n"""
            +"""  CREATE TRIGGER %(name)s\n"""
            +"""  %(time)s %(event)s ON %(table)s\n"""
            +"""  FOR EACH ROW EXECUTE PROCEDURE func_%(name)s();\n"""
            ) % locals()

class TriggerSet(base.TriggerSet):
    def drop(self):
        cursor = self.cursor()
        cursor.execute("SELECT pg_class.relname, pg_trigger.tgname FROM pg_trigger LEFT JOIN pg_class ON (pg_trigger.tgrelid = pg_class.oid) WHERE pg_trigger.tgname LIKE 'denorm_%%';")
        for table_name, trigger_name in cursor.fetchall():
            cursor.execute("DROP TRIGGER %s ON %s;" % (trigger_name, table_name))
            transaction.commit_unless_managed(using=self.using)

    def install(self):
        cursor = self.cursor()
        for name, trigger in self.triggers.iteritems():
            cursor.execute(trigger.sql())
            transaction.commit_unless_managed(using=self.using)
