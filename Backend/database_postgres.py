import psycopg2

def pg_connection():

    conn = psycopg2.connect(
        host="localhost",
        database="invoice_management",
        user="postgres",
        password="Bourbon005",
        port="5432"
    )

    return conn