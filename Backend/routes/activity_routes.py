from flask import Blueprint, jsonify
from database_postgres import pg_connection
from psycopg2.extras import RealDictCursor

activity_bp = Blueprint("activity_bp", __name__)


def create_activity_table():
    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            activity_id SERIAL PRIMARY KEY,

            activity_type VARCHAR(100) NOT NULL,
            action VARCHAR(50) NOT NULL,

            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,

            reference_id INTEGER,
            reference_number VARCHAR(150),

            user_id INTEGER,
            user_name VARCHAR(255),

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# CALLIN NEW ACTIVITY
def add_activity(
    activity_type,
    action,
    title,
    description,
    reference_id=None,
    reference_number=None,
    user_id=None,
    user_name=None,
    conn=None
):
    own_connection = False

    if conn is None:
        conn = pg_connection()
        own_connection = True

    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO activity_logs (
                activity_type,
                action,
                title,
                description,
                reference_id,
                reference_number,
                user_id,
                user_name
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            activity_type,
            action,
            title,
            description,
            reference_id,
            reference_number,
            user_id,
            user_name
        ))

        if own_connection:
            conn.commit()

    finally:
        cur.close()

        if own_connection:
            conn.close()