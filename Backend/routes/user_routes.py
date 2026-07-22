
# from flask import Blueprint, request, jsonify
# from database_postgres import pg_connection
# from psycopg2.extras import RealDictCursor
# from routes.activity_routes import add_activity

# user_bp = Blueprint("user_bp", __name__)

# # CREATE TABLE
# def user():

#     conn = pg_connection()
#     cur = conn.cursor()

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS users(
#             id SERIAL PRIMARY KEY,
#             user_name VARCHAR(100),
#             password VARCHAR(100) NOT NULL,
#             role VARCHAR(50),
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)

#     conn.commit()
#     cur.close()
#     conn.close()
    
    
# # LOGIN 
# @user_bp.route("/login", methods=["POST"])
# def login():

#     data = request.get_json()

#     conn = pg_connection()
#     cur = conn.cursor(cursor_factory=RealDictCursor)

#     cur.execute("""
#         SELECT *
#         FROM users
#         WHERE
#             user_name=%s
#             AND password=%s
#             AND LOWER(role)=LOWER(%s)
#     """,(
#         data["user_name"],
#         data["password"],
#         data["role"]
#     ))

#     user = cur.fetchone()

#     cur.close()
#     conn.close()

#     if user:

#         return jsonify({
#             "message":"Login Successful",
#             "user":user
#         })

#     return jsonify({
#         "message":"Invalid Username, Password or Role"
#     }),401 


# # CREATE USER
# @user_bp.route("/user", methods=["POST"])
# def add_user():

#     data = request.get_json()
    
#     role = data.get("role", "User")

#     conn = pg_connection()
#     cur = conn.cursor()

#     cur.execute("""
#         INSERT INTO users(
#             user_name,
#             password,
#             role
#         )
#         VALUES (%s, %s, %s)
#         RETURNING id
#     """, (
#         data.get("user_name"),
#         data.get("password"),
#         data.get("role")
#     ))
#     created_user_id = cur.fetchone()[0]
#     add_activity(
#     activity_type="user",
#     action="created",
#     title="New user added",
#     description=f'User "{data.get("user_name")}" has been added',
#     reference_id=created_user_id,
#     user_id=data.get("logged_user_id"),
#     user_name=data.get("logged_user_name"),
#     conn=conn
# )

#     conn.commit()

#     cur.close()
#     conn.close()

#     return jsonify({
#         "message": "User Added Successfully"
#     })


# # GET ALL USERS
# @user_bp.route("/users", methods=["GET"])
# def get_users():

#     conn = pg_connection()
#     cur = conn.cursor()

#     cur.execute("""
#         SELECT
#             id,
#             user_name,
#             password,
#             role,
#             created_at
#         FROM users
#         ORDER BY id DESC
#     """)

#     rows = cur.fetchall()

#     result = []

#     for row in rows:
#         result.append({
#             "id": row[0],
#             "user_name": row[1],
#             "password": row[2],
#             "role":row[3],
#             "created_at": str(row[4])
#         })

#     cur.close()
#     conn.close()

#     return jsonify(result)


# # UPDATE USER
# @user_bp.route("/user/<int:id>", methods=["PUT"])
# def update_user(id):

#     data = request.get_json()

#     conn = pg_connection()
#     cur = conn.cursor()

#     cur.execute("""
#         UPDATE users
#         SET
#             user_name=%s,
#             password=%s,
#             role=%s
#         WHERE id=%s
#     """, (
#         data["user_name"],
#         data["password"],
#         data["role"],
#         id
#     ))
#     add_activity(
#     activity_type="user",
#     action="updated",
#     title="User updated",
#     description=f'User "{data.get("user_name")}" has been updated',
#     reference_id=id,
#     user_id=data.get("logged_user_id"),
#     user_name=data.get("logged_user_name"),
#     conn=conn
# )

#     conn.commit()

#     cur.close()
#     conn.close()

#     return jsonify({
#         "message": "User Updated Successfully"
#     })


# # DELETE USER
# @user_bp.route("/user/<int:user_id>", methods=["DELETE"])
# def delete_user(user_id):
#     data = request.get_json(silent=True) or {}

#     actor_user_id = data.get("actor_user_id")
#     actor_user_name = data.get("actor_user_name")

#     conn = pg_connection()
#     cur = conn.cursor()

#     try:
#         cur.execute("""
#             SELECT user_name
#             FROM users
#             WHERE id = %s
#         """, (user_id,))

#         user = cur.fetchone()

#         if not user:
#             return jsonify({
#                 "message": "User not found"
#             }), 404

#         deleted_user_name = user[0]

#         add_activity(
#             activity_type="user",
#             action="deleted",
#             title="User Deleted",
#             description=f'User "{deleted_user_name}" has been deleted',
#             reference_id=user_id,
#             user_id=actor_user_id,
#             user_name=actor_user_name,
#             conn=conn
#         )

#         cur.execute("""
#             DELETE FROM users
#             WHERE id = %s
#         """, (user_id,))

#         conn.commit()

#         return jsonify({
#             "message": "User deleted successfully"
#         }), 200

#     except Exception as e:
#         conn.rollback()

#         return jsonify({
#             "message": "Error deleting user",
#             "error": str(e)
#         }), 500

#     finally:
#         cur.close()
#         conn.close()

import hmac
from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_csrf_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies
)
from psycopg2.extras import RealDictCursor
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from database_postgres import pg_connection
from routes.activity_routes import add_activity
from routes.auth_utils import admin_required


user_bp = Blueprint(
    "user_bp",
    __name__
)


# =========================================================
# HELPERS
# =========================================================

def normalize_role(role):
    role_value = str(
        role or ""
    ).strip().lower()

    if role_value == "admin":
        return "Admin"

    if role_value == "user":
        return "User"

    return None


def is_password_hash(value):
    password_value = str(
        value or ""
    )

    hash_prefixes = (
        "scrypt:",
        "pbkdf2:",
        "argon2:",
        "bcrypt:"
    )

    return password_value.startswith(
        hash_prefixes
    )


def verify_password(
    stored_password,
    submitted_password
):
    """
    Support both existing plaintext passwords
    and new password hashes during migration.
    """

    stored_value = str(
        stored_password or ""
    )

    submitted_value = str(
        submitted_password or ""
    )

    if is_password_hash(stored_value):
        try:
            return check_password_hash(
                stored_value,
                submitted_value
            )
        except ValueError:
            return False

    return hmac.compare_digest(
        stored_value,
        submitted_value
    )


def safe_user_object(user):
    return {
        "id": user["id"],
        "user_id": user["id"],
        "user_name": user["user_name"],
        "role": user["role"],
        "created_at": (
            str(user["created_at"])
            if user.get("created_at")
            else None
        )
    }


def get_authenticated_actor():
    claims = get_jwt()

    try:
        user_id = int(
            get_jwt_identity()
        )
    except (TypeError, ValueError):
        user_id = None

    return {
        "user_id": user_id,
        "user_name":
            claims.get("user_name")
    }


# =========================================================
# CREATE / UPDATE USERS TABLE
# =========================================================

def user():
    conn = pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,

                user_name VARCHAR(100),

                password VARCHAR(255)
                    NOT NULL,

                role VARCHAR(50),

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Existing password column is VARCHAR(100).
        # Increase it safely for password hashes.
        cur.execute("""
            ALTER TABLE users
            ALTER COLUMN password
            TYPE VARCHAR(255)
        """)

        # Prevent duplicate usernames irrespective
        # of uppercase/lowercase differences.
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                users_username_lower_unique
            ON users (LOWER(user_name))
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# =========================================================
# LOGIN
# =========================================================

@user_bp.route(
    "/login",
    methods=["POST"]
)
def login():
    data = request.get_json(
        silent=True
    ) or {}

    user_name = str(
        data.get("user_name", "")
    ).strip()

    submitted_password = str(
        data.get("password", "")
    )

    requested_role = normalize_role(
        data.get("role")
    )

    if (
        not user_name
        or not submitted_password
        or not requested_role
    ):
        return jsonify({
            "message":
                "Username, password and role are required"
        }), 400

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
                role,
                created_at
            FROM users
            WHERE LOWER(user_name) =
                  LOWER(%s)
            LIMIT 1
        """, (user_name,))

        found_user = cur.fetchone()

        if not found_user:
            return jsonify({
                "message":
                    "Invalid username, password or role"
            }), 401

        actual_role = normalize_role(
            found_user["role"]
        )

        if actual_role != requested_role:
            return jsonify({
                "message":
                    "Invalid username, password or role"
            }), 401

        if not verify_password(
            found_user["password"],
            submitted_password
        ):
            return jsonify({
                "message":
                    "Invalid username, password or role"
            }), 401

        # Automatically migrate an existing plaintext
        # password after the first successful login.
        if not is_password_hash(
            found_user["password"]
        ):
            hashed_password = (
                generate_password_hash(
                    submitted_password
                )
            )

            cur.execute("""
                UPDATE users
                SET password = %s
                WHERE id = %s
            """, (
                hashed_password,
                found_user["id"]
            ))

            conn.commit()

        token = create_access_token(
            identity=str(
                found_user["id"]
            ),
            additional_claims={
                "role": actual_role,
                "user_name":
                    found_user["user_name"]
            },
            expires_delta=timedelta(
                hours=8
            )
        )

        user_response = safe_user_object({
            **found_user,
            "role": actual_role
        })

        response = jsonify({
            "message":
                "Login successful",
            "user": user_response,
            "csrf_token":
                get_csrf_token(token)
        })

        set_access_cookies(
            response,
            token
        )

        return response, 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Unable to complete login",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# =========================================================
# LOGOUT
# =========================================================

@user_bp.route(
    "/logout",
    methods=["POST"]
)
def logout():
    response = jsonify({
        "message":
            "Logged out successfully"
    })

    unset_jwt_cookies(response)

    return response, 200


# =========================================================
# AUTHENTICATED USER
# =========================================================

@user_bp.route(
    "/me",
    methods=["GET"]
)
@jwt_required()
def get_current_user():
    jwt_data = get_jwt()

    try:
        user_id = int(
            get_jwt_identity()
        )
    except (TypeError, ValueError):
        return jsonify({
            "message":
                "Invalid authentication session"
        }), 401

    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT
                id,
                user_name,
                role,
                created_at
            FROM users
            WHERE id = %s
        """, (user_id,))

        found_user = cur.fetchone()

        if not found_user:
            return jsonify({
                "message":
                    "Authenticated user no longer exists"
            }), 401

        found_user["role"] = (
            normalize_role(
                found_user["role"]
            ) or "User"
        )

        return jsonify({
            "user":
                safe_user_object(found_user),
            "csrf_token":
                jwt_data.get("csrf")
        }), 200

    except Exception as error:
        return jsonify({
            "message":
                "Unable to verify authentication",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# =========================================================
# CREATE USER — ADMIN ONLY
# =========================================================

@user_bp.route(
    "/user",
    methods=["POST"]
)
@admin_required
def add_user():
    data = request.get_json(
        silent=True
    ) or {}

    user_name = str(
        data.get("user_name", "")
    ).strip()

    password = str(
        data.get("password", "")
    )

    role = normalize_role(
        data.get("role")
    )

    if not user_name:
        return jsonify({
            "message":
                "Username is required"
        }), 400

    if len(user_name) < 3:
        return jsonify({
            "message":
                "Username must contain at least 3 characters"
        }), 400

    if len(password) < 8:
        return jsonify({
            "message":
                "Password must contain at least 8 characters"
        }), 400

    if not role:
        return jsonify({
            "message":
                "Role must be Admin or User"
        }), 400

    actor = get_authenticated_actor()

    conn = pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id
            FROM users
            WHERE LOWER(user_name) =
                  LOWER(%s)
        """, (user_name,))

        if cur.fetchone():
            return jsonify({
                "message":
                    "Username already exists"
            }), 409

        hashed_password = (
            generate_password_hash(
                password
            )
        )

        cur.execute("""
            INSERT INTO users (
                user_name,
                password,
                role
            )
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            user_name,
            hashed_password,
            role
        ))

        created_user_id = (
            cur.fetchone()[0]
        )

        add_activity(
            activity_type="user",
            action="created",
            title="New user added",
            description=(
                f'User "{user_name}" '
                f'has been added'
            ),
            reference_id=
                created_user_id,
            user_id=
                actor["user_id"],
            user_name=
                actor["user_name"],
            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "User added successfully",
            "user": {
                "id": created_user_id,
                "user_id":
                    created_user_id,
                "user_name": user_name,
                "role": role
            }
        }), 201

    except Exception as error:
        conn.rollback()

        error_text = str(error)

        if (
            "unique" in
            error_text.lower()
            or "duplicate" in
            error_text.lower()
        ):
            return jsonify({
                "message":
                    "Username already exists"
            }), 409

        return jsonify({
            "message":
                "Unable to add user",
            "error": error_text
        }), 500

    finally:
        cur.close()
        conn.close()


# =========================================================
# FETCH USERS — ADMIN ONLY
# =========================================================

@user_bp.route(
    "/users",
    methods=["GET"]
)
@admin_required
def get_users():
    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT
                id,
                user_name,
                role,
                created_at
            FROM users
            ORDER BY id DESC
        """)

        rows = cur.fetchall()

        return jsonify([
            safe_user_object({
                **row,
                "role": (
                    normalize_role(
                        row["role"]
                    ) or "User"
                )
            })
            for row in rows
        ]), 200

    except Exception as error:
        return jsonify({
            "message":
                "Unable to fetch users",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# =========================================================
# UPDATE USER — ADMIN ONLY
# =========================================================

@user_bp.route(
    "/user/<int:user_id>",
    methods=["PUT"]
)
@admin_required
def update_user(user_id):
    data = request.get_json(
        silent=True
    ) or {}

    user_name = str(
        data.get("user_name", "")
    ).strip()

    role = normalize_role(
        data.get("role")
    )

    new_password = str(
        data.get("new_password")
        or data.get("password")
        or ""
    )

    confirm_password = str(
        data.get("confirm_password")
        or ""
    )

    if not user_name:
        return jsonify({
            "message":
                "Username is required"
        }), 400

    if not role:
        return jsonify({
            "message":
                "Role must be Admin or User"
        }), 400

    if new_password:
        if len(new_password) < 8:
            return jsonify({
                "message":
                    "Password must contain at least 8 characters"
            }), 400

        if (
            confirm_password
            and new_password !=
            confirm_password
        ):
            return jsonify({
                "message":
                    "Passwords do not match"
            }), 400

    actor = get_authenticated_actor()

    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT
                id,
                user_name,
                role
            FROM users
            WHERE id = %s
            FOR UPDATE
        """, (user_id,))

        existing_user = cur.fetchone()

        if not existing_user:
            return jsonify({
                "message":
                    "User not found"
            }), 404

        cur.execute("""
            SELECT id
            FROM users
            WHERE LOWER(user_name) =
                  LOWER(%s)
              AND id <> %s
        """, (
            user_name,
            user_id
        ))

        if cur.fetchone():
            return jsonify({
                "message":
                    "Username already exists"
            }), 409

        existing_role = normalize_role(
            existing_user["role"]
        )

        if (
            existing_role == "Admin"
            and role != "Admin"
        ):
            cur.execute("""
                SELECT COUNT(*)
                FROM users
                WHERE LOWER(role) = 'admin'
            """)

            admin_count = (
                cur.fetchone()["count"]
            )

            if admin_count <= 1:
                return jsonify({
                    "message":
                        "The last administrator cannot be changed to User"
                }), 409

        if new_password:
            hashed_password = (
                generate_password_hash(
                    new_password
                )
            )

            cur.execute("""
                UPDATE users
                SET
                    user_name = %s,
                    role = %s,
                    password = %s
                WHERE id = %s
            """, (
                user_name,
                role,
                hashed_password,
                user_id
            ))

        else:
            cur.execute("""
                UPDATE users
                SET
                    user_name = %s,
                    role = %s
                WHERE id = %s
            """, (
                user_name,
                role,
                user_id
            ))

        add_activity(
            activity_type="user",
            action="updated",
            title="User updated",
            description=(
                f'User "{user_name}" '
                f'has been updated'
            ),
            reference_id=user_id,
            user_id=
                actor["user_id"],
            user_name=
                actor["user_name"],
            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "User updated successfully",
            "user": {
                "id": user_id,
                "user_id": user_id,
                "user_name": user_name,
                "role": role
            }
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Unable to update user",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# =========================================================
# DELETE USER — ADMIN ONLY
# =========================================================

@user_bp.route(
    "/user/<int:user_id>",
    methods=["DELETE"]
)
@admin_required
def delete_user(user_id):
    actor = get_authenticated_actor()

    if actor["user_id"] == user_id:
        return jsonify({
            "message":
                "You cannot delete your own logged-in account"
        }), 409

    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT
                id,
                user_name,
                role
            FROM users
            WHERE id = %s
            FOR UPDATE
        """, (user_id,))

        existing_user = cur.fetchone()

        if not existing_user:
            return jsonify({
                "message":
                    "User not found"
            }), 404

        if (
            normalize_role(
                existing_user["role"]
            ) == "Admin"
        ):
            cur.execute("""
                SELECT COUNT(*)
                FROM users
                WHERE LOWER(role) = 'admin'
            """)

            admin_count = (
                cur.fetchone()["count"]
            )

            if admin_count <= 1:
                return jsonify({
                    "message":
                        "The last administrator cannot be deleted"
                }), 409

        deleted_user_name = (
            existing_user["user_name"]
        )

        add_activity(
            activity_type="user",
            action="deleted",
            title="User deleted",
            description=(
                f'User "{deleted_user_name}" '
                f'has been deleted'
            ),
            reference_id=user_id,
            user_id=
                actor["user_id"],
            user_name=
                actor["user_name"],
            conn=conn
        )

        cur.execute("""
            DELETE FROM users
            WHERE id = %s
        """, (user_id,))

        conn.commit()

        return jsonify({
            "message":
                "User deleted successfully"
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error deleting user",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()