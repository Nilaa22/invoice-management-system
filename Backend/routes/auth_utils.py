from functools import wraps

from flask import jsonify
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required
)


def get_logged_user_id():
    """
    Return the authenticated user's ID as an integer.
    """

    identity = get_jwt_identity()

    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def admin_required(function):
    """
    Require a valid JWT and an Admin role.
    """

    @wraps(function)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        claims = get_jwt()

        role = str(
            claims.get("role", "")
        ).strip().lower()

        if role != "admin":
            return jsonify({
                "message":
                    "Administrator access is required"
            }), 403

        return function(*args, **kwargs)

    return decorated_function