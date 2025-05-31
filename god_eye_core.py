from fetch_schema import fetch_schema_from_db
from sql_runner import run_sql_query, check_sql_columns
import openai
import difflib
import re

MAX_ATTEMPTS = 3

def find_closest(name, options):
    matches = difflib.get_close_matches(name, options, n=1)
    return matches[0] if matches else None


def clean_sql(sql):
    # Remove code fences and leading/trailing whitespace
    return re.sub(r"^```(?:sql)?|```$", "", sql, flags=re.IGNORECASE | re.MULTILINE).strip()

def generate_sql_and_results(user_input, openai_api_key, db_params=None):
    openai.api_key = openai_api_key

    # Fetch schema for the correct database
    all_tables, all_columns, primary_keys, foreign_keys = fetch_schema_from_db(db_params)
    print('DB params:', db_params)
    print('All tables:', all_tables)
    def build_schema_summary():
        summary = "Database schema:\n"
        summary += "Tables:\n"
        for table in all_tables:
            summary += f"  - {table}\n"
        summary += "Columns per table:\n"
        for table, columns in all_columns.items():
            summary += f"  {table}: {columns}\n"
        return summary

    schema_summary = build_schema_summary()
    prompt = (
        f"{schema_summary}\n"
        "# Example: SELECT products.product_name, products.price FROM products ORDER BY products.price DESC LIMIT 5;\n"
        "# IMPORTANT: Always qualify column names with their table name or alias (e.g., table.column), especially when joining tables."
        "# IMPORTANT: Use only the table and column names listed above. If a requested column does not exist, use the closest matching column(s) from the schema."
        "Write only the SQL query (no explanation) for PostgreSQL, using the exact table and column names from the schema above, for this request: "
        "Be aware that most recent dates in the folder is "
        "{'min_birth_date': datetime.date(1937, 9, 19), 'max_birth_date': datetime.date(1966, 1, 27), 'min_order_date': datetime.date(1996, 7, 4), 'max_order_date': datetime.date(1998, 5, 6), 'min_required_date': datetime.date(1996, 7, 24), 'max_required_date': datetime.date(1998, 6, 11), 'min_shipped_date': datetime.date(1996, 7, 10), 'max_shipped_date': datetime.date(1998, 5, 6)}"
        "based on this adjust the SQL query to match the user's request: "
        f"{user_input}"
    )
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        sql_query = response.choices[0].message.content.strip()
        sql_query = clean_sql(sql_query)  # <-- Clean code fences
        table, bad_col = check_sql_columns(sql_query, all_columns)
        if bad_col:
            # Try to find the closest column name
            closest = find_closest(bad_col, all_columns.get(table, []))
            if closest:
                # Replace the bad column with the closest match and try again
                sql_query = sql_query.replace(bad_col, closest)
                attempts += 1
                continue
            else:
                return sql_query, None, f"The column '{bad_col}' does not exist in '{table}'. Available columns: {all_columns[table]}"
        else:
            print("Final SQL query:", sql_query)
            try:
                results = run_sql_query(sql_query, db_params)
                return sql_query, results, None
            except Exception as e:
                # If error is due to syntax, try again
                print("SQL execution error:", e)
                attempts += 1
                continue
    return sql_query, None, f"Failed to generate a valid SQL query after {MAX_ATTEMPTS} attempts."