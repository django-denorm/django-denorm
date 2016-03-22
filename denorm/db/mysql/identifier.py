from django.db import connection

def get_name():
    return '@denorm_identifier'

def set():
    """
    Set a MySQL user defined variable to control DirtyInstance.identifier
    """
    cursor = connection.cursor()
    cursor.execute('SET {} = uuid();'.format(get_name()))
    cursor.close()

def get():
    cursor = connection.cursor()
    cursor.execute('SELECT {};'.format(get_name()))
    identifier = cursor.fetchone()[0]
    cursor.close()
    return identifier
