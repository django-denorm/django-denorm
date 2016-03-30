from .fields import cached, denormalized, CountField, CacheKeyField
from .denorms import flush, rebuildall
from .dependencies import depend_on_related

from django.conf import settings
if hasattr(settings, 'DENORM_FLUSH_AFTER_REQUEST'):
    import warnings
    warnings.warn("The DENORM_FLUSH_AFTER_REQUEST will be deprecated in favor of the new DenormMiddleware", DeprecationWarning)

if hasattr(settings, 'DENORM_FLUSH_AFTER_REQUEST') and settings.DENORM_FLUSH_AFTER_REQUEST:
    from django.core.signals import request_finished

    def do_flush(sender, **kwargs):
        flush()
    request_finished.connect(do_flush)

__all__ = ['cached', 'denormalized', 'depend_on_related', 'flush', 'rebuildall', 'CountField', 'CacheKeyField']
