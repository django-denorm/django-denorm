from denorm.db import base

class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.model._meta.db_table
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

class Trigger(base.Trigger):

    def sql(self):
        name = self.name()
        actions = (";\n   ").join(set([a.sql() for a in self.actions if a.sql()])) + ";"
        table = self.model._meta.db_table
        time = self.time.upper()
        event = self.event.upper()

        return (
             """ CREATE TRIGGER %(name)s\n"""
            +"""  %(time)s %(event)s ON %(table)s\n"""
            +"""  FOR EACH ROW BEGIN\n"""
            +"""   %(actions)s\n  END \n"""
            ) % locals()

class TriggerSet(base.TriggerSet):

    def install(self):
        from django.db import connection
        cursor = connection.cursor()

        cursor.execute("SHOW TRIGGERS;")
        for result in cursor.fetchall():
            if result[0].startswith("denorm_"):
                cursor.execute("""DROP TRIGGER %s;""" % result[0])

        for name,trigger in self.triggers.iteritems():
            cursor.execute(trigger.sql())
