
# from flask import Blueprint, jsonify, request
# from werkzeug.security import (
#     check_password_hash,
#     generate_password_hash
# )

# from database_postgres import pg_connection
# from psycopg2.extras import RealDictCursor


# profile_bp = Blueprint(
#     "profile_bp",
#     __name__
# )


# # --------------------------------------------------
# # FETCH LOGGED-IN USER PROFILE
# # --------------------------------------------------

# @profile_bp.route(
#     "/profile/<int:user_id>",
#     methods=["GET"]
# )
# def get_profile(user_id):
#     conn = pg_connection()

#     cur = conn.cursor(
#         cursor_factory=RealDictCursor
#     )

#     try:
#         cur.execute("""
#             SELECT
#                 id,
#                 user_name,
#                 password,
#                 role
#             FROM users
#             WHERE id = %s
#         """, (user_id,))

#         user = cur.fetchone()

#         if not user:
#             return jsonify({
#                 "message": "User not found"
#             }), 404

#         return jsonify({
#             "user_id": user["id"],
#             "user_name": user["user_name"],
#             "password":user["password"],
#             "role": user["role"]
#         }), 200

#     except Exception as error:
#         return jsonify({
#             "message": "Error fetching profile",
#             "error": str(error)
#         }), 500

#     finally:
#         cur.close()
#         conn.close()


# # --------------------------------------------------
# # UPDATE USERNAME
# # --------------------------------------------------

# @profile_bp.route(
#     "/profile/<int:user_id>",
#     methods=["PUT"]
# )
# def update_profile(user_id):
#     data = request.get_json() or {}

#     user_name = str(
#         data.get("user_name", "")
#     ).strip()

#     if not user_name:
#         return jsonify({
#             "message": "Username is required"
#         }), 400

#     conn = pg_connection()
#     cur = conn.cursor()

#     try:
#         # Check whether another user already has
#         # the same username.
#         cur.execute("""
#             SELECT id
#             FROM users
#             WHERE LOWER(user_name) = LOWER(%s)
#               AND id <> %s
#         """, (
#             user_name,
#             user_id
#         ))

#         existing_user = cur.fetchone()

#         if existing_user:
#             return jsonify({
#                 "message": "Username already exists"
#             }), 409

#         cur.execute("""
#             UPDATE users
#             SET user_name = %s
#             WHERE id = %s
#             RETURNING id
#         """, (
#             user_name,
#             user_id
#         ))

#         updated_user = cur.fetchone()

#         if not updated_user:
#             conn.rollback()

#             return jsonify({
#                 "message": "User not found"
#             }), 404

#         conn.commit()

#         return jsonify({
#             "message": "Username updated successfully",
#             "user_id": user_id,
#             "user_name": user_name
#         }), 200

#     except Exception as error:
#         conn.rollback()

#         return jsonify({
#             "message": "Error updating username",
#             "error": str(error)
#         }), 500

#     finally:
#         cur.close()
#         conn.close()


# # --------------------------------------------------
# # CHANGE PASSWORD
# # --------------------------------------------------

# @profile_bp.route("/change-password/<int:user_id>", methods=["PUT"])
# def change_password(user_id):

#     data = request.get_json()

#     new_password = data.get("new_password")
#     confirm_password = data.get("confirm_password")

#     if not new_password or not confirm_password:
#         return jsonify({
#             "message": "Please fill all password fields"
#         }), 400

#     if new_password != confirm_password:
#         return jsonify({
#             "message": "Passwords do not match"
#         }), 400

#     conn = pg_connection()
#     cur = conn.cursor()

#     try:

#         cur.execute("""
#             UPDATE users
#             SET password=%s
#             WHERE id=%s
#         """, (
#             new_password,
#             user_id
#         ))

#         conn.commit()

#         return jsonify({
#             "message": "Password updated successfully"
#         }), 200

#     except Exception as e:

#         conn.rollback()

#         return jsonify({
#             "message": "Unable to update password",
#             "error": str(e)
#         }), 500

#     finally:
#         cur.close()
#         conn.close()

import hmac

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required
)
from psycopg2.extras import RealDictCursor
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from database_postgres import pg_connection
from routes.activity_routes import add_activity


profile_bp = Blueprint(
    "profile_bp",
    __name__
)


# =========================================================
# HELPERS
# =========================================================

def is_password_hash(value):
    password_value = str(
        value or ""
    )

    return password_value.startswith((
        "scrypt:",
        "pbkdf2:",
        "argon2:",
        "bcrypt:"
    ))


def password_matches(
    stored_password,
    submitted_password
):
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


def authenticated_user_id():
    try:
        return int(
            get_jwt_identity()
        )
    except (TypeError, ValueError):
        return None


def validate_legacy_user_id(
    requested_user_id
):
    """
    Allow old frontend URLs temporarily, but stop a
    user from requesting another user's profile.
    """

    current_user_id = (
        authenticated_user_id()
    )

    if current_user_id is None:
        return None, (
            jsonify({
                "message":
                    "Invalid authentication session"
            }),
            401
        )

    if (
        requested_user_id is not None
        and requested_user_id !=
        current_user_id
    ):
        return None, (
            jsonify({
                "message":
                    "You cannot access another user's profile"
            }),
            403
        )

    return current_user_id, None


# =========================================================
# GET PROFILE
# =========================================================

@profile_bp.route(
    "/profile",
    methods=["GET"]
)
@profile_bp.route(
    "/profile/<int:requested_user_id>",
    methods=["GET"]
)
@jwt_required()
def get_profile(
    requested_user_id=None
):
    user_id, error_response = (
        validate_legacy_user_id(
            requested_user_id
        )
    )

    if error_response:
        return error_response

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
                    "User not found"
            }), 404

        return jsonify({
            "user_id":
                found_user["id"],
            "id":
                found_user["id"],
            "user_name":
                found_user["user_name"],
            "role":
                found_user["role"],
            "created_at": (
                str(found_user["created_at"])
                if found_user["created_at"]
                else None
            )
        }), 200

    except Exception as error:
        return jsonify({
            "message":
                "Error fetching profile",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# =========================================================
# UPDATE USERNAME
# =========================================================

@profile_bp.route(
    "/profile",
    methods=["PUT"]
)
@profile_bp.route(
    "/profile/<int:requested_user_id>",
    methods=["PUT"]
)
@jwt_required()
def update_profile(
    requested_user_id=None
):
    user_id, error_response = (
        validate_legacy_user_id(
            requested_user_id
        )
    )

    if error_response:
        return error_response

    data = request.get_json(
        silent=True
    ) or {}

    user_name = str(
        data.get("user_name", "")
    ).strip()

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

    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT
                id,
                user_name
            FROM users
            WHERE id = %s
            FOR UPDATE
        """, (user_id,))

        current_user = cur.fetchone()

        if not current_user:
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

        cur.execute("""
            UPDATE users
            SET user_name = %s
            WHERE id = %s
        """, (
            user_name,
            user_id
        ))

        add_activity(
            activity_type="user",
            action="updated",
            title="Profile updated",
            description=(
                f'User "{user_name}" '
                f'updated their profile'
            ),
            reference_id=user_id,
            user_id=user_id,
            user_name=user_name,
            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "Username updated successfully",
            "user": {
                "id": user_id,
                "user_id": user_id,
                "user_name": user_name
            }
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error updating username",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# =========================================================
# CHANGE PASSWORD
# =========================================================

@profile_bp.route(
    "/change-password",
    methods=["PUT"]
)
@profile_bp.route(
    "/change-password/<int:requested_user_id>",
    methods=["PUT"]
)
@jwt_required()
def change_password(
    requested_user_id=None
):
    user_id, error_response = (
        validate_legacy_user_id(
            requested_user_id
        )
    )

    if error_response:
        return error_response

    data = request.get_json(
        silent=True
    ) or {}

    current_password = str(
        data.get("current_password", "")
    )

    new_password = str(
        data.get("new_password", "")
    )

    confirm_password = str(
        data.get("confirm_password", "")
    )

    if (
        not current_password
        or not new_password
        or not confirm_password
    ):
        return jsonify({
            "message":
                "Current password, new password and confirmation are required"
        }), 400

    if len(new_password) < 8:
        return jsonify({
            "message":
                "New password must contain at least 8 characters"
        }), 400

    if new_password != confirm_password:
        return jsonify({
            "message":
                "New password and confirmation do not match"
        }), 400

    if current_password == new_password:
        return jsonify({
            "message":
                "New password must be different from the current password"
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
                password
            FROM users
            WHERE id = %s
            FOR UPDATE
        """, (user_id,))

        found_user = cur.fetchone()

        if not found_user:
            return jsonify({
                "message":
                    "User not found"
            }), 404

        if not password_matches(
            found_user["password"],
            current_password
        ):
            return jsonify({
                "message":
                    "Current password is incorrect"
            }), 401

        hashed_password = (
            generate_password_hash(
                new_password
            )
        )

        cur.execute("""
            UPDATE users
            SET password = %s
            WHERE id = %s
        """, (
            hashed_password,
            user_id
        ))

        add_activity(
            activity_type="user",
            action="updated",
            title="Password changed",
            description=(
                f'User "{found_user["user_name"]}" '
                f'changed their password'
            ),
            reference_id=user_id,
            user_id=user_id,
            user_name=
                found_user["user_name"],
            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "Password changed successfully"
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Unable to change password",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()