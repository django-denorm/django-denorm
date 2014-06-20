from django.db import transaction
from denorm.db import base


class RandomBigInt(base.RandomBigInt):
    def sql(self):
        return '(9223372036854775806::INT8 * ((RANDOM()-0.5)*2.0) )::INT8'


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

        sql = (
            'BEGIN\n'
            '    INSERT INTO %(table)s %(columns)s %(values)s;\n'
            'EXCEPTION WHEN unique_violation THEN\n'
            '    -- do nothing\n'
            'END'
        ) % locals()
        return sql, params


class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        params = []
        updates = ", ".join(["%s = %s" % (k, v) for k, v in zip(self.columns, self.values)])
        if isinstance(self.where, tuple):
            where, where_params = self.where
        else:
            where, where_params = self.where, []
        params.extend(where_params)
        return 'UPDATE %(table)s SET %(updates)s WHERE %(where)s' % locals(), params


class Trigger(base.Trigger):
    def name(self):
        name = base.Trigger.name(self)
        if self.content_type_field:
            name += "_%s" % self.content_type
        return name

    def sql(self):
        name = self.name()
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
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()
        content_type = self.content_type
        ct_field = self.content_type_field

        conditions = []

        if event == "UPDATE":
            for field, native_type in self.fields:
                if native_type is None:
                    # If Django didn't know what this field type should be
                    # then compare it as text - Fixes a problem of trying to
                    # compare PostGIS geometry fields.
                    conditions.append("(OLD.%(f)s::%(t)s IS DISTINCT FROM NEW.%(f)s::%(t)s)" % {'f': field, 't': 'text'})
                else:
                    conditions.append("(OLD.%(f)s IS DISTINCT FROM NEW.%(f)s)" % {'f': field})

            conditions = ["(%s)" % " OR ".join(conditions)]

        if ct_field:
            if event == "UPDATE":
                conditions.append("(OLD.%(ctf)s = %(ct)s) OR (NEW.%(ctf)s = %(ct)s)" % {'ctf': ct_field, 'ct': content_type})
            elif event == "INSERT":
                conditions.append("(NEW.%s = %s)" % (ct_field, content_type))
            elif event == "DELETE":
                conditions.append("(OLD.%s = %s)" % (ct_field, content_type))

        if conditions:
            cond = " AND ".join(conditions)
            actions = "\n            ".join(action_list)
            actions = """IF %(cond)s THEN
            %(actions)s
        END IF;""" % locals()
        else:
            actions = "\n        ".join(action_list)

        sql = """
CREATE OR REPLACE FUNCTION func_%(name)s()
    RETURNS TRIGGER AS $$
    BEGIN
        %(actions)s
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER %(name)s
    %(time)s %(event)s ON %(table)s
    FOR EACH ROW EXECUTE PROCEDURE func_%(name)s();
""" % locals()
        return sql, params


class TriggerSet(base.TriggerSet):
    def drop(self):
        cursor = self.cursor()
        cursor.execute("SELECT pg_class.relname, pg_trigger.tgname FROM pg_trigger LEFT JOIN pg_class ON (pg_trigger.tgrelid = pg_class.oid) WHERE pg_trigger.tgname LIKE 'denorm_%%';")
        for table_name, trigger_name in cursor.fetchall():
            cursor.execute('DROP TRIGGER %s ON %s;' % (trigger_name, table_name))
            transaction.commit_unless_managed(using=self.using)

    def install(self):
        cursor = self.cursor()
        cursor.execute("SELECT lanname FROM pg_catalog.pg_language WHERE lanname ='plpgsql'")
        if not cursor.fetchall():
            cursor.execute('CREATE LANGUAGE plpgsql')
        for name, trigger in self.triggers.iteritems():
            sql, args = trigger.sql()
            cursor.execute(sql, args)
            transaction.commit_unless_managed(using=self.using)
