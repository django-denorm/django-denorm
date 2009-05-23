# -*- coding: utf-8 -*-
from django.db import models

def find_fks(from_model, to_model, fk_name=None):
    """
    Finds all ForeignKeys on 'from_model' pointing to 'to_model'.
    If 'fk_name' is given only ForeignKeys matching that name are returned.
    """
    # get all ForeignKeys
    fkeys = [x for x in from_model._meta.fields if isinstance(x,models.ForeignKey)]

    # filter out all FKs not pointing to 'to_model'
    fkeys = [x for x in fkeys if repr(x.rel.to).lower() == repr(to_model).lower()]

    # if 'fk_name' was given, filter out all FKs not matching that name, leaving
    # only one (or none)
    if fk_name:
        fk_name = fk_name if isinstance(fk_name,(str,unicode)) else fk_name.attname
        fkeys = [x for x in fkeys if x.attname in (fk_name,fk_name+'_id')]

    return fkeys

def find_m2ms(from_model, to_model, m2m_name=None):
    """
    Finds all ManyToManyFields on 'from_model' pointing to 'to_model'.
    If 'm2m_name' is given only ManyToManyFields matching that name are returned.
    """
    # get all ManyToManyFields
    m2ms = from_model._meta.many_to_many

    # filter out all M2Ms not pointing to 'to_model'
    m2ms = [x for x in m2ms if repr(x.rel.to).lower() == repr(to_model).lower()]

    # if 'm2m_name' was given, filter out all M2Ms not matching that name, leaving
    # only one (or none)
    if m2m_name:
        m2m_name = m2m_name if isinstance(m2m_name,(str,unicode)) else m2m_name.attname
        m2ms = [x for x in m2ms if x.attname == m2m_name]

    return m2ms
