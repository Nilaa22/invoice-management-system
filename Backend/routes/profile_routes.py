
from flask import Blueprint, jsonify, request
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from database_postgres import pg_connection
from psycopg2.extras import RealDictCursor


profile_bp = Blueprint(
    "profile_bp",
    __name__
)


# --------------------------------------------------
# FETCH LOGGED-IN USER PROFILE
# --------------------------------------------------

@profile_bp.route(
    "/profile/<int:user_id>",
    methods=["GET"]
)
def get_profile(user_id):
    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT
                id,
                user_name,
                password,
                role
            FROM users
            WHERE id = %s
        """, (user_id,))

        user = cur.fetchone()

        if not user:
            return jsonify({
                "message": "User not found"
            }), 404

        return jsonify({
            "user_id": user["id"],
            "user_name": user["user_name"],
            "password":user["password"],
            "role": user["role"]
        }), 200

    except Exception as error:
        return jsonify({
            "message": "Error fetching profile",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# --------------------------------------------------
# UPDATE USERNAME
# --------------------------------------------------

@profile_bp.route(
    "/profile/<int:user_id>",
    methods=["PUT"]
)
def update_profile(user_id):
    data = request.get_json() or {}

    user_name = str(
        data.get("user_name", "")
    ).strip()

    if not user_name:
        return jsonify({
            "message": "Username is required"
        }), 400

    conn = pg_connection()
    cur = conn.cursor()

    try:
        # Check whether another user already has
        # the same username.
        cur.execute("""
            SELECT id
            FROM users
            WHERE LOWER(user_name) = LOWER(%s)
              AND id <> %s
        """, (
            user_name,
            user_id
        ))

        existing_user = cur.fetchone()

        if existing_user:
            return jsonify({
                "message": "Username already exists"
            }), 409

        cur.execute("""
            UPDATE users
            SET user_name = %s
            WHERE id = %s
            RETURNING id
        """, (
            user_name,
            user_id
        ))

        updated_user = cur.fetchone()

        if not updated_user:
            conn.rollback()

            return jsonify({
                "message": "User not found"
            }), 404

        conn.commit()

        return jsonify({
            "message": "Username updated successfully",
            "user_id": user_id,
            "user_name": user_name
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message": "Error updating username",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# --------------------------------------------------
# CHANGE PASSWORD
# --------------------------------------------------

@profile_bp.route("/change-password/<int:user_id>", methods=["PUT"])
def change_password(user_id):

    data = request.get_json()

    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not new_password or not confirm_password:
        return jsonify({
            "message": "Please fill all password fields"
        }), 400

    if new_password != confirm_password:
        return jsonify({
            "message": "Passwords do not match"
        }), 400

    conn = pg_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            UPDATE users
            SET password=%s
            WHERE id=%s
        """, (
            new_password,
            user_id
        ))

        conn.commit()

        return jsonify({
            "message": "Password updated successfully"
        }), 200

    except Exception as e:

        conn.rollback()

        return jsonify({
            "message": "Unable to update password",
            "error": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()