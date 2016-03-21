# -*- coding: utf-8 -*-
from denorm import flush
from django.db import DatabaseError
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class DenormMiddleware(object):
    """
    Calls ``denorm.flush`` during the response stage of every request. If your data mostly or only changes during requests
    this should be a good idea. If you run into performance problems with this (because ``flush()`` takes
    to long to complete) you can try using a daemon or handle flushing manually instead.

    As usual the order of middleware classes matters. It makes a lot of sense to put ``DenormMiddleware``
    after ``TransactionMiddleware`` in your ``MIDDLEWARE_CLASSES`` setting.
    """
    def process_response(self, request, response):
        try:
            flush()
        except DatabaseError as e:
            logger.error(e)
        return response


class DenormMysqlConnectionIdentifierMiddleware(object):
    """
    Sets a MySQL user defined variable to control DirtyInstance.identifier
    """
    def process_request(self, request):
        cursor = connection.cursor()
        cursor.execute('SET @denorm_identifier = uuid();')
