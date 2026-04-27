import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MKCL\MSSQLSERVER01;"
    "DATABASE=DB_MusicTracker;"
    "Trusted_Connection=yes;"
    "MARS_Connection=yes;"
)

def get_connection():
    conn = pyodbc.connect(CONN_STR)
    return conn, conn.cursor()

# This function runs a single query in SQL, and returns results as a dataframe.
def run_query(query, params=None, one=False):
    import pyodbc
    import pandas as pd

    conn, cur = get_connection()

    try:
        df = pd.read_sql_query(query, conn, params=params)

        # force full materialization (important)
        df = df.copy()

        if one:
            return df.to_dict(orient="records")[0] if not df.empty else None

        return df

    finally:
        conn.close()

# This function runs multiple queries in SQL, returning the results zipped
# together in a single dictionary.
def run_multi(query_list, params_list):
    import pyodbc
    import pandas as pd

    conn, cur = get_connection()

    try:
        results = []

        for q, p in zip(query_list, params_list):
            df = pd.read_sql_query(q, conn, params=p)
            df = df.copy()
            results.append(df)

        return results

    finally:
        conn.close()

# This function executes SQL CRUD other than SELECT. (INSERT, UPDATE, DELETE)
def run_execute(query, params=None):
    import pyodbc

    try:
        conn, cur = get_connection()
        cur.execute(query, params or ())
        conn.commit()
        return cur.rowcount  # useful sometimes
    finally:
        conn.close()

# This function executes multiple SQL CRUD using run_execute.
def run_transaction(queries):
    import pyodbc
    conn, cur = get_connection()

    try:
        for q, p in queries:
            cur.execute(q, p or ())
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

# This function is used when SGV snapshots are created.
def run_snapshot_transaction(insert_snapshot_sql, insert_songs_sql, rows):
    import pyodbc

    conn, cur = get_connection()

    try:
        # ----------------------------
        # 1. Insert snapshot + get ID
        # ----------------------------
        cur.execute(insert_snapshot_sql)
        snapshot_id = cur.fetchone()[0]

        # ----------------------------
        # 2. Attach snapshot_id
        # ----------------------------
        rows_with_snapshot = [(snapshot_id, *row) for row in rows]

        # ----------------------------
        # 3. Insert all songs
        # ----------------------------
        cur.fast_executemany = True
        cur.executemany(insert_songs_sql, rows_with_snapshot)

        # ----------------------------
        # 4. Commit everything
        # ----------------------------
        conn.commit()

        return snapshot_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()

# This function is used for name fixing.
def run_transaction_fn(fn):
    conn, cur = get_connection()

    try:
        result = fn(cur)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

# This function replaces NaN and other invalid values with empty strings in a df.
def replace_na(df):
    df = df.replace([float("inf"), float("-inf")], None)
    df = df.fillna("")
    return df