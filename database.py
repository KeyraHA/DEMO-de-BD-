# database.py
import psycopg2
import psycopg2.extras

def get_connection():
    return psycopg2.connect(
        host='localhost',
        port=5432,
        dbname='ProyectoBD',
        user='postgres',
        password='postgres'
    )

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