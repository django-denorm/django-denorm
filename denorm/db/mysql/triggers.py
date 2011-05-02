from denorm.db import base
import random
import string


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

        return """ INSERT IGNORE INTO %(table)s %(columns)s %(values)s """ % locals()

class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        updates = ','.join(["%s=%s"%(k,v) for k,v in zip(self.columns,self.values)])
        where = self.where

        return """ UPDATE %(table)s SET %(updates)s WHERE %(where)s """ % locals()

class Trigger(base.Trigger):

    def sql(self):
        name = self.name()
        if len(name) > 50:
            name = name[:45] + ''.join(
                random.choice(string.ascii_uppercase + string.digits)
                for x in range(5)
            )
        actions = (";\n   ").join(set([a.sql() for a in self.actions if a.sql()])) + ";"
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()

        if event == "UPDATE":
            conditions = list()
            for field, native_type in self.fields:
                # TODO: find out if we need to compare some fields as text like in postgres
                conditions.append("( OLD.%(f)s <> NEW.%(f)s )" % {'f': field,})

            cond = "(%s)"%"OR".join(conditions)
        else:
            cond = 'TRUE'

        return (
             """ CREATE TRIGGER %(name)s\n"""
            +"""  %(time)s %(event)s ON %(table)s\n"""
            +"""  FOR EACH ROW BEGIN\n"""
            +"""   IF %(cond)s THEN\n"""
            +"""    %(actions)s\n"""
            +"""   END IF;\n"""
            +"""  END;\n"""
            ) % locals()

class TriggerSet(base.TriggerSet):

    def install(self):
        if self.using:
            from django.db import connections
            connection = connections[self.using]
        else:
            from django.db import connection
        cursor = connection.cursor()

        cursor.execute("SHOW TRIGGERS;")
        for result in cursor.fetchall():
            if result[0].startswith("denorm_"):
                cursor.execute("""DROP TRIGGER %s;""" % result[0])

        for name,trigger in self.triggers.iteritems():
            cursor.execute(trigger.sql())
