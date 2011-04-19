from denorm.db import base
from django.db import DatabaseError

class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.table
        where = ",".join(["%s=%s"%(k,v) for k,v in self.kwargs.iteritems()])
        return """ SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s """ % locals()

class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "("+",".join(self.columns)+")"
        if isinstance(self.values,TriggerNestedSelect):
            values = ""+self.values.sql()+""
        else:
            values = "VALUES("+",".join(self.values)+")"

        return """ INSERT OR REPLACE INTO %(table)s %(columns)s %(values)s """ % locals()

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

        when = []
        if event == "UPDATE":
            when.append("("+"OR".join(["(OLD.%s IS NOT NEW.%s)"%(f,f) for f,t in self.fields])+")")
        if ct_field:
            if event == "DELETE":
                when.append("(OLD.%s==%s)" % (ct_field, content_type))
            elif event == "INSERT":
                when.append("(NEW.%s==%s)" % (ct_field, content_type))
            elif event == "UPDATE":
                when.append("((OLD.%(ctf)s==%(ct)s)OR(NEW.%(ctf)s==%(ct)s))" % {'ctf': ct_field, 'ct': content_type})

        when = "AND".join(when)
        if when:
            when = "WHEN(%s)" % (when,)

        return (
             """ CREATE TRIGGER %(name)s\n"""
            +"""  %(time)s %(event)s ON %(table)s\n"""
            +"""  FOR EACH ROW %(when)s BEGIN\n"""
            +"""   %(actions)s\n  END;\n"""
            ) % locals()

class TriggerSet(base.TriggerSet):

    def install(self):
        from django.db import connection
        cursor = connection.cursor()

        for name,trigger in self.triggers.iteritems():
            try:
                cursor.execute(trigger.sql())
            except DatabaseError:
                cursor.execute("DROP TRIGGER "+trigger.name())
                cursor.execute(trigger.sql())
