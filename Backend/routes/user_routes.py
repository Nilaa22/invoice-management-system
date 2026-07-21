
from flask import Blueprint, request, jsonify
from database_postgres import pg_connection
from psycopg2.extras import RealDictCursor
from routes.activity_routes import add_activity

user_bp = Blueprint("user_bp", __name__)

# CREATE TABLE
def user():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            user_name VARCHAR(100),
            password VARCHAR(100) NOT NULL,
            role VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    
    
# LOGIN 
@user_bp.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    conn = pg_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM users
        WHERE
            user_name=%s
            AND password=%s
            AND LOWER(role)=LOWER(%s)
    """,(
        data["user_name"],
        data["password"],
        data["role"]
    ))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:

        return jsonify({
            "message":"Login Successful",
            "user":user
        })

    return jsonify({
        "message":"Invalid Username, Password or Role"
    }),401 


# CREATE USER
@user_bp.route("/user", methods=["POST"])
def add_user():

    data = request.get_json()
    
    role = data.get("role", "User")

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users(
            user_name,
            password,
            role
        )
        VALUES (%s, %s, %s)
        RETURNING id
    """, (
        data.get("user_name"),
        data.get("password"),
        data.get("role")
    ))
    created_user_id = cur.fetchone()[0]
    add_activity(
    activity_type="user",
    action="created",
    title="New user added",
    description=f'User "{data.get("user_name")}" has been added',
    reference_id=created_user_id,
    user_id=data.get("logged_user_id"),
    user_name=data.get("logged_user_name"),
    conn=conn
)

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "message": "User Added Successfully"
    })


# GET ALL USERS
@user_bp.route("/users", methods=["GET"])
def get_users():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            user_name,
            password,
            role,
            created_at
        FROM users
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append({
            "id": row[0],
            "user_name": row[1],
            "password": row[2],
            "role":row[3],
            "created_at": str(row[4])
        })

    cur.close()
    conn.close()

    return jsonify(result)


# UPDATE USER
@user_bp.route("/user/<int:id>", methods=["PUT"])
def update_user(id):

    data = request.get_json()

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET
            user_name=%s,
            password=%s,
            role=%s
        WHERE id=%s
    """, (
        data["user_name"],
        data["password"],
        data["role"],
        id
    ))
    add_activity(
    activity_type="user",
    action="updated",
    title="User updated",
    description=f'User "{data.get("user_name")}" has been updated',
    reference_id=id,
    user_id=data.get("logged_user_id"),
    user_name=data.get("logged_user_name"),
    conn=conn
)

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "message": "User Updated Successfully"
    })


# DELETE USER
@user_bp.route("/user/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    data = request.get_json(silent=True) or {}

    actor_user_id = data.get("actor_user_id")
    actor_user_name = data.get("actor_user_name")

    conn = pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT user_name
            FROM users
            WHERE id = %s
        """, (user_id,))

        user = cur.fetchone()

        if not user:
            return jsonify({
                "message": "User not found"
            }), 404

        deleted_user_name = user[0]

        add_activity(
            activity_type="user",
            action="deleted",
            title="User Deleted",
            description=f'User "{deleted_user_name}" has been deleted',
            reference_id=user_id,
            user_id=actor_user_id,
            user_name=actor_user_name,
            conn=conn
        )

        cur.execute("""
            DELETE FROM users
            WHERE id = %s
        """, (user_id,))

        conn.commit()

        return jsonify({
            "message": "User deleted successfully"
        }), 200

    except Exception as e:
        conn.rollback()

        return jsonify({
            "message": "Error deleting user",
            "error": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()