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

    def sql(self):
        name = self.name()
        actions = (";\n   ").join(set([a.sql() for a in self.actions if a.sql()])) + ";"
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()

        if event == "UPDATE":
            cond = "(%s)"%"OR".join(["(OLD.%s!=NEW.%s)"%(f,f) for f in self.fieldnames])
        else:
            cond = 'TRUE'

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

    def install(self):
        from django.db import connection, transaction
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM pg_trigger;")
        for result in cursor.fetchall():
            if result[1].startswith("denorm_"):
                x,table = result[1].rsplit("_on_",)
                cursor.execute("""DROP TRIGGER %s ON %s;""" % (result[1],table))
                transaction.commit_unless_managed()

        for name,trigger in self.triggers.iteritems():
            cursor.execute(trigger.sql())
            transaction.commit_unless_managed()
