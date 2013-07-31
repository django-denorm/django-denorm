from django.db import transaction
from denorm.db import base


import logging

logger = logging.getLogger('denorm-sqlite')

class RandomBigInt(base.RandomBigInt):
    def sql(self):
        return 'RANDOM()'


class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.table
        where = ",".join(["%s = %s" % (k, v) for k, v in self.kwargs.iteritems()])
        return 'SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s' % locals(), tuple()


class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "(" + ",".join(self.columns) + ")"
        if isinstance(self.values, TriggerNestedSelect):
            sql, params = self.values.sql()
            values = ""+ sql +""
        else:
            values = "VALUES(" + ",".join(self.values) + ")"
            params = []

        return 'INSERT OR REPLACE INTO %(table)s %(columns)s %(values)s' % locals(), tuple(params)


class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        updates = ','.join(["%s=%s"%(k, v) for k, v in zip(self.columns, self.values)])
        if isinstance(self.where, tuple):
            where, where_params = self.where
        else:
            where, where_params = self.where, []

        return 'UPDATE %(table)s SET %(updates)s WHERE %(where)s' % locals(), where_params


class TriggerConditionFieldChange(base.TriggerConditionFieldChange):
    def sql(self, actions):
        actions, params = super(TriggerConditionFieldChange, self).sql(actions)
        when = ["(" + "OR".join(["(OLD.%s IS NOT NEW.%s)" % (f, f) for f in self.field_names]) + ")"]
        when = "AND".join(when)
        when = "WHEN(%s)" % (when,)

        return """
    FOR EACH ROW %(when)s BEGIN
        %(actions)s
    END;
""" % locals(), tuple(params)

class Trigger(base.Trigger):

    def name(self):
        name = base.Trigger.name(self)
        if self.content_type_field:
            name += "_%s" % self.content_type
        return name

    def sql(self, name):
        actions, params = super(Trigger, self).sql()
        if not self.condition:
            actions = """
        FOR EACH ROW BEGIN
        %(actions)s
        END;
""" % locals()

        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()

        return """
CREATE TRIGGER %(name)s
    %(time)s %(event)s ON %(table)s
    %(actions)s
""" % locals(), tuple(params)


class TriggerSet(base.TriggerSet):
    def drop(self):
        cursor = self.cursor()

        cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'denorm_%%';")
        for trigger_name, table_name in cursor.fetchall():
            cursor.execute("DROP TRIGGER %s;" % (trigger_name,))
            transaction.commit_unless_managed(using=self.using)

    def install(self):
        cursor = self.cursor()

        for name, triggers in self.triggers.iteritems():
            for i, trigger in enumerate(triggers):
                sql, args = trigger.sql(name + "_%s" % i)
                cursor.execute(sql, args)
                transaction.commit_unless_managed(using=self.using)
