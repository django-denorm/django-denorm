from denorm.db import base

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

    def sql(self):
        name = self.name()
        actions = (";\n   ").join(set([a.sql() for a in self.actions if a.sql()])) + ";"
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()


        if event == "UPDATE":
            when = "WHEN(%s)"%"OR".join(["(OLD.%s!=NEW.%s)"%(f,f) for f in self.fieldnames])
        else:
            when = ''

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
            except:
                cursor.execute("DROP TRIGGER "+trigger.name())
                cursor.execute(trigger.sql())
