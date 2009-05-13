from django.db import models

def find_fk(from_model, to_model, foreign_key=None):
    if foreign_key:
        if not isinstance(foreign_key, (str, unicode)):
            foreign_key = foreign_key.attname
        fkeys = filter(lambda x: isinstance(x, models.ForeignKey)
                                 and unicode(x.rel.to).lower() == unicode(to_model).lower()
                                 and x.attname in [foreign_key,foreign_key+'_id'],
                       from_model._meta.fields)
    else:
        fkeys = filter(lambda x: isinstance(x, models.ForeignKey)
                                 and unicode(x.rel.to).lower() == unicode(to_model).lower(),
                       from_model._meta.fields)

    if not fkeys:
        return None
    if len(fkeys) > 1:
        raise ValueError("%s has more than one ForeignKey to %s;"
                         " please specify which one to use."
                         % (from_model, to_model))
    if fkeys[0].attname.endswith("_id"):
        return fkeys[0].attname[:-3]
    else:
        return fkeys[0].attname
