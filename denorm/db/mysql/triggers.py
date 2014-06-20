import random
import string
from denorm.db import base


class RandomBigInt(base.RandomBigInt):
    def sql(self):
        return '(9223372036854775806 * ((RAND()-0.5)*2.0) )'


class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.table
        where = ", ".join(["%s = %s" % (k, v) for k, v in self.kwargs.iteritems()])
        return 'SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s' % locals(), tuple()


class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "(" + ", ".join(self.columns) + ")"
        params = []
        if isinstance(self.values, TriggerNestedSelect):
            sql, nested_params = self.values.sql()
            values = "(" + sql + ")"
            params.extend(nested_params)
        else:
            values = "VALUES (" + ", ".join(self.values) + ")"

        return 'INSERT IGNORE INTO %(table)s %(columns)s %(values)s' % locals(), tuple()


class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        updates = ", ".join(["%s = %s" % (k, v) for k, v in zip(self.columns, self.values)])
        if isinstance(self.where, tuple):
            where, where_params = self.where
        else:
            where, where_params = self.where, []

        return 'UPDATE %(table)s SET %(updates)s WHERE %(where)s' % locals(), tuple(where_params)


class Trigger(base.Trigger):

    def sql(self):
        name = self.name()
        if len(name) > 50:
            name = name[:45] + ''.join(
                random.choice(string.ascii_uppercase + string.digits)
                for x in range(5)
            )
        params = []
        action_list = []
        for a in self.actions:
            sql, action_params = a.sql()
            if sql:
                if not sql.endswith(';'):
                    sql += ';'
                action_list.extend(sql.split('\n'))
                params.extend(action_params)

        # FIXME: actions should depend on content_type and content_type_field, if applicable
        # now we flag too many things dirty, e.g. a change for ('forum', 1) also flags ('post', 1)
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()

        conditions = []

        if event == "UPDATE":
            for field, native_type in self.fields:
                # TODO: find out if we need to compare some fields as text like in postgres
                conditions.append("(NOT(OLD.%(f)s <=> NEW.%(f)s))" % {'f': field})

        if conditions:
            cond = " OR ".join(conditions)
            actions = "\n            ".join(action_list)
            actions = """
        IF %(cond)s THEN
            %(actions)s
        END IF;
            """ % locals()
        else:
            actions = "\n        ".join(action_list)

        sql = """
CREATE TRIGGER %(name)s
    %(time)s %(event)s ON %(table)s
    FOR EACH ROW BEGIN
        %(actions)s
    END;
""" % locals()
        return sql, tuple(params)


class TriggerSet(base.TriggerSet):
    def drop(self):
        cursor = self.cursor()

        # FIXME: according to MySQL docs the LIKE statement should work
        # but it doesn't. MySQL reports a Syntax Error
        #cursor.execute(r"SHOW TRIGGERS WHERE Trigger LIKE 'denorm_%%'")
        cursor.execute('SHOW TRIGGERS')
        for result in cursor.fetchall():
            if result[0].startswith('denorm_'):
                cursor.execute('DROP TRIGGER %s;' % result[0])

    def install(self):
        cursor = self.cursor()
        for name, trigger in self.triggers.iteritems():
            sql, args = trigger.sql()
            cursor.execute(sql, args)
