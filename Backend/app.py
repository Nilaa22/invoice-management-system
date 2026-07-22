# from flask import Flask
# from flask_cors import CORS

# from routes.customer_routes import customer_bp,customer
# from routes.user_routes import user_bp,user
# from routes.product_routes import product_bp,product
# from routes.company_routes import company_bp,company
# from routes.profile_routes import profile_bp
# from routes.pi_routes import pi_bp,pi
# from routes.ti_routes import ti_bp,ti
# from routes.dashboard_routes import dashboard_bp
# from routes.activity_routes import activity_bp,create_activity_table
# from routes.analytics_routes import analytics_bp
# from routes.utils_routes import utils_bp
# from routes.pdf_routes import pdf_bp



# # from database import db_connection
# app = Flask(__name__)
# CORS(app,origins="*")

# app.register_blueprint(customer_bp)
# app.register_blueprint(user_bp)
# app.register_blueprint(product_bp)
# app.register_blueprint(company_bp)
# app.register_blueprint(profile_bp)
# app.register_blueprint(pi_bp)
# app.register_blueprint(ti_bp)
# app.register_blueprint(dashboard_bp)
# app.register_blueprint(activity_bp)
# app.register_blueprint(analytics_bp)
# app.register_blueprint(utils_bp)
# app.register_blueprint(pdf_bp)

# # Initialize database tables when the module is imported
# customer()
# user()
# product()
# company()
# pi()
# ti()
# create_activity_table()
# if __name__ == "__main__":
#     app.run(debug=True,host="0.0.0.0",port=5000)




import os
from datetime import timedelta

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from routes.activity_routes import (
    activity_bp,
    create_activity_table
)
from routes.analytics_routes import (
    analytics_bp
)
from routes.company_routes import (
    company,
    company_bp
)
from routes.customer_routes import (
    customer,
    customer_bp
)
from routes.dashboard_routes import (
    dashboard_bp
)
from routes.pdf_routes import pdf_bp
from routes.pi_routes import pi, pi_bp
from routes.product_routes import (
    product,
    product_bp
)
from routes.profile_routes import (
    profile_bp
)
from routes.ti_routes import ti, ti_bp
from routes.user_routes import (
    user,
    user_bp
)
from routes.utils_routes import utils_bp


def environment_boolean(
    variable_name,
    default=False
):
    value = os.environ.get(
        variable_name
    )

    if value is None:
        return default

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on"
    }


app = Flask(__name__)


# =========================================================
# JWT CONFIGURATION
# =========================================================

jwt_secret_key = os.environ.get(
    "JWT_SECRET_KEY"
)

if not jwt_secret_key:
    if os.environ.get("RENDER"):
        raise RuntimeError(
            "JWT_SECRET_KEY is missing from Render environment variables"
        )

    jwt_secret_key = (
        "local-development-only-"
        "replace-this-secret"
    )


app.config.update(
    JWT_SECRET_KEY=jwt_secret_key,

    JWT_TOKEN_LOCATION=[
        "cookies"
    ],

    JWT_ACCESS_COOKIE_NAME=
        "invoice_access_token",

    JWT_ACCESS_COOKIE_PATH="/",

    JWT_COOKIE_SECURE=
        environment_boolean(
            "JWT_COOKIE_SECURE",
            default=True
        ),

    JWT_COOKIE_SAMESITE="None",

    JWT_COOKIE_CSRF_PROTECT=True,

    JWT_CSRF_IN_COOKIES=True,

    JWT_ACCESS_CSRF_COOKIE_NAME=
        "csrf_access_token",

    JWT_ACCESS_CSRF_HEADER_NAME=
        "X-CSRF-TOKEN",

    JWT_ACCESS_TOKEN_EXPIRES=
        timedelta(hours=8),

    JWT_SESSION_COOKIE=True
)


jwt = JWTManager(app)


# =========================================================
# CORS
# =========================================================

allowed_origins = [
    "http://localhost:5173",
    "https://lovely-granita-8e223b.netlify.app"
]


CORS(
    app,
    resources={
        r"/*": {
            "origins":
                allowed_origins
        }
    },
    supports_credentials=True,
    allow_headers=[
        "Content-Type",
        "X-CSRF-TOKEN"
    ],
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS"
    ]
)


# =========================================================
# JWT ERROR RESPONSES
# =========================================================

@jwt.unauthorized_loader
def missing_token_callback(reason):
    return jsonify({
        "message":
            "Authentication is required",
        "error": reason
    }), 401


@jwt.invalid_token_loader
def invalid_token_callback(reason):
    return jsonify({
        "message":
            "Authentication token is invalid",
        "error": reason
    }), 401


@jwt.expired_token_loader
def expired_token_callback(
    jwt_header,
    jwt_payload
):
    return jsonify({
        "message":
            "Your login session has expired"
    }), 401


@jwt.revoked_token_loader
def revoked_token_callback(
    jwt_header,
    jwt_payload
):
    return jsonify({
        "message":
            "Authentication token has been revoked"
    }), 401


@jwt.needs_fresh_token_loader
def fresh_token_callback(
    jwt_header,
    jwt_payload
):
    return jsonify({
        "message":
            "A fresh login is required"
    }), 401


# =========================================================
# BLUEPRINTS
# =========================================================

app.register_blueprint(
    customer_bp
)

app.register_blueprint(
    user_bp
)

app.register_blueprint(
    product_bp
)

app.register_blueprint(
    company_bp
)

app.register_blueprint(
    profile_bp
)

app.register_blueprint(
    pi_bp
)

app.register_blueprint(
    ti_bp
)

app.register_blueprint(
    dashboard_bp
)

app.register_blueprint(
    activity_bp
)

app.register_blueprint(
    analytics_bp
)

app.register_blueprint(
    utils_bp
)

app.register_blueprint(
    pdf_bp
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

customer()
user()
product()
company()
pi()
ti()
create_activity_table()


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )