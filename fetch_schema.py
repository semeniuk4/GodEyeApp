import psycopg2

def fetch_tables_and_columns(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    all_columns = {}
    all_tables = set()
    for table, column in cursor.fetchall():
        all_tables.add(table)
        all_columns.setdefault(table, []).append(column)
    cursor.close()
    return sorted(all_tables), all_columns

def fetch_primary_keys(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            kcu.table_name,
            kcu.column_name
        FROM
            information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
        WHERE
            tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_schema = 'public'
    """)
    primary_keys = {}
    for table, column in cursor.fetchall():
        primary_keys.setdefault(table, []).append(column)
    cursor.close()
    return primary_keys

def fetch_foreign_keys(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            tc.table_name AS table_name,
            kcu.column_name AS column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM
            information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
    """)
    foreign_keys = {}
    for table, column, foreign_table, foreign_column in cursor.fetchall():
        foreign_keys.setdefault(table, []).append({
            "column": column,
            "references_table": foreign_table,
            "references_column": foreign_column
        })
    cursor.close()
    return foreign_keys

def fetch_schema_from_db(db_params=None):
    if db_params is None:
        db_params = {
            "dbname": "postgres",
            "user": "postgres",
            "password": "dancecovery",
            "host": "database-2.c9ggk84co759.eu-central-1.rds.amazonaws.com",
            "port": "5432"
        }
    print("Connecting to database with params:", db_params)
    try:
        conn = psycopg2.connect(**db_params)
        print("Connected to database successfully")
    except psycopg2.Error as e:
        print("Failed to connect to database:", e)
        return None, None, None, None
    all_tables, all_columns = fetch_tables_and_columns(conn)
    print("All tables:", all_tables)
    primary_keys = fetch_primary_keys(conn)
    foreign_keys = fetch_foreign_keys(conn)
    conn.close()
    return all_tables, all_columns, primary_keys, foreign_keys