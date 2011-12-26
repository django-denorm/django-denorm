# -*- coding: utf-8 -*-
from denorm import flush


class DenormMiddleware(object):
    """
    Calls ``denorm.flush`` during the response stage of every request. If your data mostly or only changes during requests
    this should be a good idea. If you run into performance problems with this (because ``flush()`` takes
    to long to complete) you can try using a daemon or handle flushing manually instead.

    As usual the order of middleware classes matters. It makes a lot of sense to put ``DenormMiddleware``
    after ``TransactionMiddleware`` in your ``MIDDLEWARE_CLASSES`` setting.
    """
    def process_response(self, request, response):
        flush()
        return response
