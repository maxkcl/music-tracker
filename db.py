import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib
import pandas as pd

load_dotenv()

driver = os.getenv("DB_DRIVER")
server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
trust_cert = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "no")

odbc_string = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"TrustServerCertificate={trust_cert};"
)
params = quote_plus(odbc_string)

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={params}",
    pool_pre_ping=True,
    future=True
)

# This function runs a single query in SQL, and returns results as a dataframe.
def run_query(query, params=None, one=False):
    with engine.connect() as conn:
        df = pd.read_sql_query(
            text(query),
            conn,
            params=params or {}
        )
        if one:
            return df.to_dict(orient="records")[0] if not df.empty else None

        return df

# This function runs multiple queries in SQL, returning the results zipped
# together in a single dictionary.
def run_multi(query_list, params_list):
    with engine.connect() as conn:
        results = []
        for q, p in zip(query_list, params_list):
            df = pd.read_sql_query(
                text(q),
                conn,
                params=p or {}
            )
            results.append(df)

        return results

# This function executes SQL CRUD other than SELECT. (INSERT, UPDATE, DELETE)
def run_execute(query, params=None):
    with engine.begin() as conn:
        result = conn.execute(
            text(query),
            params or {}
        )

        return result.rowcount

# This function executes multiple SQL CRUD using execute.
def run_transaction(queries):
    with engine.begin() as conn:
        for q, p in queries:
            conn.execute(
                text(q),
                p or {}
            )

# This function is used when SGV snapshots are created.
def run_snapshot_transaction(insert_snapshot_sql, insert_songs_sql, rows):
    with engine.begin() as conn:

        result = conn.execute(
            text(insert_snapshot_sql)
        )

        snapshot_id = result.fetchone()[0]

        rows_with_snapshot = []

        for row in rows:

            rows_with_snapshot.append({
                "snapshot_id": snapshot_id,
                "song_id": row[0],
                "rating": row[1],
                "tp": row[2],
                "n1s": row[3],
                "mic": row[4],
                "plays": row[5],
                "decayed_plays": row[6],
                "base_rating": row[7],
                "legacy_score": row[8],
                "recency_score": row[9]
            })

        conn.execute(
            text(insert_songs_sql),
            rows_with_snapshot
        )

        return snapshot_id

# This function is used for name fixing.
def run_transaction_fn(fn):
    conn = get_connection()
    cur = conn.cursor()

    try:
        result = fn(cur)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

# This function replaces NaN and other invalid values with empty strings in a df.
def replace_na(df):
    df = df.replace([float("inf"), float("-inf")], None)
    df = df.fillna("")
    return df