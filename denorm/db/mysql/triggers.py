import random
import string
from denorm.db import base
from . import identifier


class RandomBigInt(base.RandomBigInt):
    def sql(self):
        return '(9223372036854775806 * ((RAND()-0.5)*2.0) )'


class TriggerNestedSelect(base.TriggerNestedSelect):
    def _get_columns(self):
        columns = self.columns.split(",")
        columns.append("(SELECT {})".format(identifier.get_name()))
        columns.append("CURRENT_TIMESTAMP")
        columns = ", ".join(columns)
        return columns

    def sql(self):
        columns = self._get_columns()
        table = self.table
        where = ", ".join(["%s = %s" % (k, v) for k, v in self.kwargs.items()])
        return 'SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s' % locals(), tuple()


class TriggerActionInsert(base.TriggerActionInsert):
    def _get_columns(self):
        return self.columns + ("identifier", "created")

    def _get_values(self):
        return self.values + ("(SELECT {})".format(identifier.get_name()), "CURRENT_TIMESTAMP")

    def sql(self):
        table = self.model._meta.db_table
        columns = self._get_columns()
        columns = "(" + ", ".join(columns) + ")"
        params = []
        if isinstance(self.values, TriggerNestedSelect):
            sql, nested_params = self.values.sql()
            values = "(" + sql + ")"
            params.extend(nested_params)
        else:
            values = self._get_values()
            values = "VALUES (" + ", ".join(values) + ")"

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
        qn = self.connection.ops.quote_name

        name = self.name()
        if len(name) > 50:
            name = name[:45] + ''.join(
                random.choice(string.ascii_uppercase + string.digits)
                for x in range(5)
            )
        params = []
        action_list = []
        actions_added = set()
        for a in self.actions:
            sql, action_params = a.sql()
            if sql:
                if not sql.endswith(';'):
                    sql += ';'
                action_params = tuple(action_params)
                if (sql, action_params) not in actions_added:
                    actions_added.add((sql, action_params))
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
                field = qn(field)
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
        qn = self.connection.ops.quote_name
        cursor = self.cursor()

        # FIXME: according to MySQL docs the LIKE statement should work
        # but it doesn't. MySQL reports a Syntax Error
        #cursor.execute(r"SHOW TRIGGERS WHERE Trigger LIKE 'denorm_%%'")
        cursor.execute('SHOW TRIGGERS')
        for result in cursor.fetchall():
            if result[0].startswith('denorm_'):
                cursor.execute('DROP TRIGGER %s;' % qn(result[0]))

    def install(self):
        cursor = self.cursor()
        for name, trigger in self.triggers.items():
            sql, args = trigger.sql()
            cursor.execute(sql, args)
