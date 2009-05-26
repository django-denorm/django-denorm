
from denorm.fields import denormalized,flush
from denorm.dependencies import depend_on_related
from denorm.shortcuts import CountField

from django.conf import settings
if hasattr(settings,'DENORM_FLUSH_AFTER_REQUEST') and settings.DENORM_FLUSH_AFTER_REQUEST:
    from django.core.signals import request_finished
    def do_flush(sender,**kwargs): flush()
    request_finished.connect(do_flush)

__all__ = ["denormalized", "depend_on_related","flush", "CountField"]


