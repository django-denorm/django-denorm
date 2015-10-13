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
        where = ", ".join(["%s = %s" % (k, v) for k, v in self.kwargs.iteritems()])
        return 'SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s' % locals(), tuple()


class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "(" + ", ".join(self.columns) + ")"
        if isinstance(self.values, TriggerNestedSelect):
            sql, params = self.values.sql()
            values = "" + sql + ""
        else:
            values = "VALUES(" + ", ".join(self.values) + ")"
            params = []

        return 'INSERT OR REPLACE INTO %(table)s %(columns)s %(values)s' % locals(), tuple(params)


class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        updates = ", ".join(["%s = %s" % (k, v) for k, v in zip(self.columns, self.values)])
        if isinstance(self.where, tuple):
            where, where_params = self.where
        else:
            where, where_params = self.where, []

        return 'UPDATE %(table)s SET %(updates)s WHERE %(where)s' % locals(), where_params


class Trigger(base.Trigger):

    def name(self):
        name = base.Trigger.name(self)
        if self.content_type_field:
            name += "_%s" % self.content_type
        return name

    def sql(self):
        qn = self.connection.ops.quote_name

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
        actions = "\n        ".join(action_list)
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()
        content_type = self.content_type
        ct_field = self.content_type_field

        when = []
        if event == "UPDATE":
            when.append("(" + "OR".join(["(OLD.%s IS NOT NEW.%s)" % (qn(f), qn(f)) for f, t in self.fields]) + ")")
        if ct_field:
            ct_field = qn(ct_field)
            if event == "DELETE":
                when.append("(OLD.%s == %s)" % (ct_field, content_type))
            elif event == "INSERT":
                when.append("(NEW.%s == %s)" % (ct_field, content_type))
            elif event == "UPDATE":
                when.append("((OLD.%(ctf)s == %(ct)s) OR (NEW.%(ctf)s == %(ct)s))" % {'ctf': ct_field, 'ct': content_type})

        when = "AND".join(when)
        if when:
            when = "WHEN(%s)" % (when,)

        return """
CREATE TRIGGER %(name)s
    %(time)s %(event)s ON %(table)s
    FOR EACH ROW %(when)s BEGIN
        %(actions)s
    END;
""" % locals(), tuple(params)


class TriggerSet(base.TriggerSet):
    def drop_atomic(self):
        qn = self.connection.ops.quote_name
        cursor = self.cursor()

        cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'denorm_%%';")
        for trigger_name, table_name in cursor.fetchall():
            cursor.execute("DROP TRIGGER %s;" % (qn(trigger_name),))

    def drop(self):
        try:
            with transaction.atomic():
                self.drop_atomic()
        except AttributeError:
            self.drop_atomic()
            transaction.commit_unless_managed(using=self.using)

    def install_atomic(self):
        cursor = self.cursor()

        for name, trigger in self.triggers.iteritems():
            sql, args = trigger.sql()
            cursor.execute(sql, args)

    def install(self):
        try:
            with transaction.atomic():
                self.install_atomic()
        except AttributeError:
            self.install_atomic()
            transaction.commit_unless_managed(using=self.using)
