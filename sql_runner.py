import psycopg2
import re
from dotenv import load_dotenv
import os


load_dotenv()

HOST_DB = os.getenv("HOST_DB")
PASSWORD_DB = os.getenv("PASSWORD_DB")
USER_DB = os.getenv("USER_DB")
DB_NAME = os.getenv("DB_NAME")



def check_sql_columns(sql, all_columns):
    # all_columns: dict of {table: [col1, col2, ...]}
    for table, columns in all_columns.items():
        # Match both table.column and just column (if table is used in FROM)
        for match in re.findall(rf"{table}\.([a-zA-Z0-9_]+)", sql):
            if match not in columns:
                return table, match
        for match in re.findall(r"\b([a-zA-Z0-9_]+)\b", sql):
            if match in columns:
                continue
    return None, None

def run_sql_query(sql, db_params=None):
    if db_params is None:
        db_params = {
            "dbname": DB_NAME,
            "user": USER_DB,
            "password": PASSWORD_DB,
            "host": HOST_DB,
            "port": "5432"
        }
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute(sql)
    try:
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in results]
    except psycopg2.errors.AmbiguousColumn as e:
        # Return a clear error message
        data = []
        return None, f"Ambiguous column error: {e}. Please qualify column names with their table name."
    except Exception:
        data = []
    cursor.close()
    conn.close()
    return data