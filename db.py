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