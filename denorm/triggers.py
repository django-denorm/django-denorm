

class TriggerNestedSelect:
    def __init__(self,model,columns,**kwargs):
        self.model = model
        self.columns = ",".join(columns)
        self.kwargs = kwargs

    def sql(self):
        columns = self.columns
        table = self.model._meta.db_table
        where = ",".join(["%s = %s"%(k,v) for k,v in self.kwargs.iteritems()])
        return """ SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s """ % locals() 
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
        table = self.model._meta.db_table
        columns = "("+",".join(self.columns)+")"
        if isinstance(self.values,TriggerNestedSelect):
            values = "("+self.values.sql()+")"
        else:
            values = "VALUES("+",".join(self.values)+")"

        return """ INSERT IGNORE INTO %(table)s %(columns)s %(values)s """ % locals()

class Trigger:

    def __init__(self,model, time, event):
        self.model = model
        self.time = time
        self.event = event
        self.actions = []

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
            self.model._meta.db_table,
        ])

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
class TriggerSet:
    def __init__(self):
        self.triggers = {}

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
        from django.db import connection
        cursor = connection.cursor()

        cursor.execute("SHOW TRIGGERS;")
        for result in cursor.fetchall():
            if result[0].startswith("denorm_"):
                cursor.execute("""DROP TRIGGER %s;""" % result[0])

        for name,trigger in self.triggers.iteritems():
            cursor.execute(trigger.sql())
