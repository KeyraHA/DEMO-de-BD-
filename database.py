# database.py
import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/ProyectoBD'
)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def query(sql, params=None, fetch='all'):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or ())
                if fetch == 'all':
                    return cur.fetchall()
                elif fetch == 'one':
                    return cur.fetchone()
                else:
                    return None
    finally:
        conn.close()