from django.db import models

def find_fks(from_model, to_model, foreign_key=None):
    if foreign_key:
        if not isinstance(foreign_key, (str, unicode)):
            foreign_key = foreign_key.attname
        fkeys = filter(lambda x: isinstance(x, models.ForeignKey)
                                 and repr(x.rel.to).lower() == repr(to_model).lower()
                                 and x.attname in [foreign_key,foreign_key+'_id'],
                       from_model._meta.fields)
    else:
        fkeys = filter(lambda x: isinstance(x, models.ForeignKey)
                                 and repr(x.rel.to).lower() == repr(to_model).lower(),
                       from_model._meta.fields)

    return fkeys

def find_m2ms(from_model, to_model, m2m_name=None):
    if m2m_name:
        if not isinstance(m2m_name, (str, unicode)):
            m2m_name = m2m_name.attname
        m2ms = filter(lambda x: repr(x.rel.to).lower() == repr(to_model).lower() and x.attname == m2m_name,
                       from_model._meta.many_to_many)
    else:
        m2ms = filter(lambda x: repr(x.rel.to).lower() == repr(to_model).lower(),
                       from_model._meta.many_to_many)

    return m2ms
