

class TriggerNestedSelect:
    def __init__(self,model,columns,**kwargs):
        self.model = model
        self.columns = columns
        self.kwargs = kwargs

    def sql(self):
        return """
            SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s
        """
class TriggerAction:
    def __init__(self):
        pass

    def sql(self):
        pass

class TriggerActionInsert(TriggerAction):
    def __init__(self,model,colums,values):
        self.model = model
        self.colums = colums
        self.values = values

    def sql(self):
        table = self.model._meta.db_table
        columns = "("+",".join(self.colums)+")"
        if isinstance(self.values,TriggerNestedSelect):
            values = self.values.sql()
        else:
            values = "VALUES("+",".join(self.values)+")"

        return """
            INSERT INTO %(table)s %(columns)s %(values)s
        """ % locals()

class Trigger:

    def __init__(self,model, time, event):
        self.model = model
        self.time = time
        self.event = event
        self.actions = []

    def append(self,action):
        self.actions.append(action)

    def sql(self):
        time = self.time
        event = self.event
        table = self.model._meta.db_table
        actions = ";\n".join(set([a.sql() for a in self.actions if a.sql()])) + ";\n"

        return """
            CREATE TRIGGER %(time)s_row_%(event)s_on_%(table)s
            AFTER UPDATE ON %(table)s
            FOR EACH ROW BEGIN %(actions)s END
        """ % locals()


