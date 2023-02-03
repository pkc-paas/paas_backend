# dbonnect.py

import psycopg2, json, sys, os, time, datetime
from psycopg2 import pool, IntegrityError, extras
import pandas as pd
from pandas.io.sql import DatabaseError

import commonfuncs as cf

# 2022-12-19: adopting different db connection way from https://github.com/DavidLacroix/postgis-mvt/blob/master/webapp/app.py
DB_PARAMETERS = {
    'host': os.environ.get('DB_SERVER',''),
    'port': int( os.environ.get('DB_PORT','') ),
    'database': os.environ.get('DB_DATABASE',''),
    'user': os.environ.get('DB_USER',''),
    'password': os.environ.get('DB_PW',''),
    'cursor_factory': extras.RealDictCursor
}

assert len(DB_PARAMETERS['password']) > 2, "Invalid DB connection password" 

threaded_postgreSQL_pool = psycopg2.pool.ThreadedConnectionPool(5, 20, **DB_PARAMETERS)
assert threaded_postgreSQL_pool, "Could not create DB connection"

cf.logmessage("DB Connected")

def makeQuery(s1, output='df', lowerCaseColumns=False, fillna=True, engine=None, noprint=False):
    '''
    output choices:
    oneValue : ex: select count(*) from table1 (output will be only one value)
    df: ex: select * from users (output will be a table)
    list: json array, like df.to_dict(orient='records')
    column: first column in output as a list. ex: select username from users
    oneJson: First row, as dict
    '''
    if not isinstance(s1,str):
        cf.logmessage("query needs to be a string")
        return False
    if ';' in s1:
        cf.logmessage("; not allowed")
        return False

    if not noprint:
        # keeping auth check and some other queries out
        skipPrint = ['where token=', '.STArea()', 'STGeomFromText']
        if not any([(x in s1) for x in skipPrint]) : 
            cf.logmessage(f"Query: {' '.join(s1.split())}")
        else: 
            cf.logmessage(f"Query: {' '.join(s1.split())[:20]}")

    ps_connection = threaded_postgreSQL_pool.getconn()

    result = None # default return value

    if output in ('oneValue','oneJson'):
        ps_cursor = ps_connection.cursor()
        ps_cursor.execute(s1)
        row = ps_cursor.fetchone()
        ps_cursor.close()
        if not row: 
            result = None
        else:
            if output == 'oneValue':
                result = list(row.values())[0]
            else:
                result = dict(row)
        
        
    elif output in ('df','list','column'):
        try:
            ps_cursor = ps_connection.cursor()
            ps_cursor.execute(s1)
            res = ps_cursor.fetchall()
            ps_cursor.close()
            if fillna:
                df = pd.DataFrame(res).fillna('')
            else:
                df = pd.DataFrame(res)
        except DatabaseError as e:
            cf.logmessage("DatabaseError!")
            cf.logmessage(e)
            raise
        
        # make all colunm headers lowercase
        if lowerCaseColumns: df.columns = [x.lower() for x in df.columns] # from https://stackoverflow.com/questions/19726029/how-can-i-make-pandas-dataframe-column-headers-all-lowercase
        
        if output=='df':
            result = df
            if not len(df):
                result = []

        elif (not len(df)): 
            result = []
        elif output == 'column':
            result = df.iloc[:,0].tolist() # .iloc[:,0] -> first column
        elif output == 'list':
            result = df.to_dict(orient='records')
        else:
            # default - df
            result = df
    else:
        cf.logmessage('invalid output type')
    
    try:
        threaded_postgreSQL_pool.putconn(ps_connection) # return threaded connnection back to pool
    except DatabaseError as e:
            cf.logmessage("DatabaseError when returning threaded connection back to pool")
            cf.logmessage(e)
    finally:
        return result


def execSQL(s1, noprint=False):
    if not noprint: cf.logmessage(' '.join(s1.split()))
    ps_connection = threaded_postgreSQL_pool.getconn()
    ps_cursor = ps_connection.cursor()
    ps_cursor.execute(s1)
    ps_connection.commit()

    affected = ps_cursor.rowcount
    ps_cursor.close()
    threaded_postgreSQL_pool.putconn(ps_connection)
    return affected


def addRow(params,tablename):
    df = pd.DataFrame([params]) 
    return addTable(df, tablename) # heck


def addTable(df, table):
    """
    From https://naysan.ca/2020/05/09/pandas-to-postgresql-using-psycopg2-bulk-insert-performance-benchmark/
    Using psycopg2.extras.execute_values() to insert the dataframe
    https://www.psycopg.org/docs/extras.html#fast-exec
    """
    # Create a list of tupples from the dataframe values
    tuples = [tuple(x) for x in df.to_numpy()]
    # Comma-separated dataframe columns
    cols = ','.join(list(df.columns))
    # SQL query to execute
    query  = "INSERT INTO %s(%s) VALUES %%s" % (table, cols)
    ps_connection = threaded_postgreSQL_pool.getconn()
    cursor = ps_connection.cursor()
    cf.logmessage(f"Adding {len(df)} rows to {table}")
    try:
        extras.execute_values(cursor, query, tuples)
        ps_connection.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        cf.logmessage("Error: %s" % error)
        ps_connection.rollback()
        cursor.close()
        threaded_postgreSQL_pool.putconn(ps_connection) # return threaded connnection back to pool
        return False
    cursor.close()
    threaded_postgreSQL_pool.putconn(ps_connection) # return threaded connnection back to pool
    return True