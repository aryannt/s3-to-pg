import json
import os
from io import StringIO
import boto3
import pandas as pd
import psycopg2
from psycopg2 import sql
from botocore.exceptions import ClientError

def connect_to_db():
    return psycopg2.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
    )

def infer_column_types(df: pd.DataFrame) -> dict:
    type_map = {
        "int64": "INT",
        "float64": "NUMERIC",
        "object": "TEXT",
        "bool": "BOOLEAN",
        "datetime64[ns]": "DATE",
    }
    return {col: type_map[str(dtype)] for col, dtype in df.dtypes.items()}

def create_table(cursor, df: pd.DataFrame, table_name="employees"):
    df.columns = df.columns.str.strip()
    pk = "EMPLOYEE_ID"
    
    if pk not in df.columns:
        raise ValueError(f"Primary key column '{pk}' not found in DataFrame columns: {df.columns.tolist()}")

    cols = infer_column_types(df)
    cols = {k.strip(): v for k, v in cols.items()}

    if pk not in cols:
        cols[pk] = "NUMERIC"

    col_defs = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(dtype))
        for col, dtype in cols.items()
    )

    schema = os.getenv("SCHEMA")
    tbl = sql.Identifier(schema, table_name) if schema else sql.Identifier(table_name)

    create_stmt = sql.SQL(
        "CREATE TABLE IF NOT EXISTS {} ({}, PRIMARY KEY ({}))"
    ).format(
        tbl,
        col_defs,
        sql.Identifier(pk.strip()),
    )

    print("Executing SQL:", create_stmt.as_string(cursor))
    cursor.execute(create_stmt)

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.replace("-", pd.NA, inplace=True)
    for col in ["EMPLOYEE_ID", "SALARY", "MANAGER_ID", "DEPARTMENT_ID"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["COMMISSION_PCT"] = pd.to_numeric(df["COMMISSION_PCT"], errors="coerce")
    df["HIRE_DATE"] = pd.to_datetime(df["HIRE_DATE"], format="%d-%b-%y", errors="coerce").dt.date
    return df

def main(event, context):
    s3 = boto3.client("s3")
    expected_columns = [
        "EMPLOYEE_ID",
        "FIRST_NAME",
        "LAST_NAME",
        "EMAIL",
        "PHONE_NUMBER",
        "HIRE_DATE",
        "JOB_ID",
        "SALARY",
        "COMMISSION_PCT",
        "MANAGER_ID",
        "DEPARTMENT_ID",
    ]

    try:
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = obj["Body"].read().decode("utf-8")
        df = pd.read_csv(StringIO(data))

        if list(df.columns) != expected_columns:
            raise ValueError(
                f"CSV schema mismatch.\nExpected: {expected_columns}\nGot: {list(df.columns)}"
            )

        df = clean_dataframe(df)
        print("Cleaned columns:", df.columns.tolist())
        conn = connect_to_db()
        cursor = conn.cursor()
        create_table(cursor, df, table_name="employees")

        schema = os.getenv("SCHEMA")
        tbl = sql.Identifier(schema, "employees") if schema else sql.Identifier("employees")
        cols_sql = sql.SQL(", ").join(map(sql.Identifier, df.columns))
        values_sql = sql.SQL(", ").join(sql.Placeholder() * len(df.columns))

        conflict_target = sql.SQL("({})").format(sql.Identifier("EMPLOYEE_ID"))

        insert_stmt = sql.SQL(
            "INSERT INTO {} ({}) VALUES ({}) "
            "ON CONFLICT {} DO UPDATE SET {}"
        ).format(
            tbl,
            cols_sql,
            values_sql, 
            conflict_target,
            sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
                for c in df.columns if c != "EMPLOYEE_ID"
            ),
        )


        for row in df.itertuples(index=False, name=None):
            cursor.execute(insert_stmt, row)
            
        cursor.execute("SELECT * FROM employees LIMIT 10;")
        print(cursor.fetchall())

        conn.commit()
        cursor.close()
        conn.close()

        print(f"[SUCCESS] Processed {len(df)} rows from s3://{bucket}/{key}")

    except Exception as e:
        print(f"[ERROR] {e}")
        raise
