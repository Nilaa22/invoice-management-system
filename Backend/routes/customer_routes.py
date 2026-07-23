import re
from psycopg2 import IntegrityError
from flask import Blueprint, request, jsonify
from database_postgres import pg_connection
from routes.activity_routes import add_activity

customer_bp = Blueprint("customer_bp", __name__)

# CREATE CUSTOMER TABLE
def customer():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers(
            id SERIAL PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            company_name VARCHAR(255) NOT NULL,
            email_address VARCHAR(255) UNIQUE NOT NULL,
            phone_number VARCHAR(50) NOT NULL,
            gst_number VARCHAR(50) UNIQUE NOT NULL,
            pan_number VARCHAR(50),

            street_address TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(100),
            pincode_zip VARCHAR(20),

            shipping_street_address TEXT,
            shipping_city VARCHAR(100),
            shipping_state VARCHAR(100),
            shipping_country VARCHAR(100),
            shipping_pincode_zip VARCHAR(20)
        )
    """)
    cur.execute(""" 
                ALTER TABLE customers
                ADD COLUMN IF NOT EXISTS created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP""")

    conn.commit()
    cur.close()
    conn.close()

# VALIDATION
def normalize_phone_number(phone_number):
    phone = re.sub(
        r"\D",
        "",
        str(phone_number or "")
    )

    # Convert 919876543210 to 9876543210
    if (
        len(phone) == 12
        and phone.startswith("91")
    ):
        phone = phone[2:]

    return phone


def normalize_gst_number(gst_number):
    return str(
        gst_number or ""
    ).strip().upper()


def normalize_email_address(email_address):
    return str(
        email_address or ""
    ).strip().lower()



# CREATE CUSTOMER

@customer_bp.route(
    "/customer",
    methods=["POST"]
)
def add_customer():
    data = request.get_json(
        silent=True
    ) or {}

    actor_user_id = data.get(
        "actor_user_id"
    )

    actor_user_name = data.get(
        "actor_user_name"
    )

    customer_name = str(
        data.get("customer_name") or ""
    ).strip()

    company_name = str(
        data.get("company_name") or ""
    ).strip()

    email_address = normalize_email_address(
        data.get("email_address")
    )

    phone_number = normalize_phone_number(
        data.get("phone_number")
    )

    gst_number = normalize_gst_number(
        data.get("gst_number")
    )

    pan_number = str(
        data.get("pan_number") or ""
    ).strip().upper()

    # ---------------------------------------
    # Required field validation
    # ---------------------------------------

    if not customer_name:
        return jsonify({
            "message":
                "Customer name is required"
        }), 400

    if not company_name:
        return jsonify({
            "message":
                "Company name is required"
        }), 400

    if not email_address:
        return jsonify({
            "message":
                "Email address is required"
        }), 400

    if len(phone_number) != 10:
        return jsonify({
            "message":
                "Please enter a valid "
                "10-digit phone number"
        }), 400

    if len(gst_number) != 15:
        return jsonify({
            "message":
                "Please enter a valid "
                "15-character GST number"
        }), 400

    conn = pg_connection()
    cur = conn.cursor()

    try:
        # ---------------------------------------
        # Check duplicate phone or GST
        # ---------------------------------------

        cur.execute("""
            SELECT
                id,
                customer_name,
                company_name,
                email_address,
                phone_number,
                gst_number

            FROM customers

            WHERE
                CASE
                    WHEN LENGTH(
                        REGEXP_REPLACE(
                            phone_number,
                            '[^0-9]',
                            '',
                            'g'
                        )
                    ) = 12

                    AND REGEXP_REPLACE(
                        phone_number,
                        '[^0-9]',
                        '',
                        'g'
                    ) LIKE '91%%'

                    THEN RIGHT(
                        REGEXP_REPLACE(
                            phone_number,
                            '[^0-9]',
                            '',
                            'g'
                        ),
                        10
                    )

                    ELSE REGEXP_REPLACE(
                        phone_number,
                        '[^0-9]',
                        '',
                        'g'
                    )
                END = %s

                OR UPPER(
                    TRIM(gst_number)
                ) = %s

            LIMIT 1
        """, (
            phone_number,
            gst_number
        ))

        duplicate_customer = cur.fetchone()

        if duplicate_customer:
            existing_phone = (
                normalize_phone_number(
                    duplicate_customer[4]
                )
            )

            existing_gst = (
                normalize_gst_number(
                    duplicate_customer[5]
                )
            )

            same_phone = (
                existing_phone ==
                phone_number
            )

            same_gst = (
                existing_gst ==
                gst_number
            )

            if same_phone and same_gst:
                message = (
                    "A customer with the same "
                    "phone number and GST number "
                    "already exists"
                )

            elif same_phone:
                message = (
                    "A customer with this phone "
                    "number already exists"
                )

            else:
                message = (
                    "A customer with this GST "
                    "number already exists"
                )

            return jsonify({
                "message": message,

                "existing_customer_id":
                    duplicate_customer[0],

                "existing_customer_name":
                    duplicate_customer[1],

                "existing_company_name":
                    duplicate_customer[2]
            }), 409

        # ---------------------------------------
        # Check duplicate email
        # Your table already has UNIQUE email.
        # This gives a cleaner error message.
        # ---------------------------------------

        cur.execute("""
            SELECT
                id,
                customer_name,
                company_name

            FROM customers

            WHERE LOWER(
                TRIM(email_address)
            ) = %s

            LIMIT 1
        """, (
            email_address,
        ))

        duplicate_email = cur.fetchone()

        if duplicate_email:
            return jsonify({
                "message":
                    "A customer with this email "
                    "address already exists",

                "existing_customer_id":
                    duplicate_email[0],

                "existing_customer_name":
                    duplicate_email[1],

                "existing_company_name":
                    duplicate_email[2]
            }), 409

        # ---------------------------------------
        # Insert customer
        # ---------------------------------------

        cur.execute("""
            INSERT INTO customers (
                customer_name,
                company_name,
                phone_number,
                email_address,
                gst_number,
                pan_number,

                street_address,
                city,
                state,
                country,
                pincode_zip,

                shipping_street_address,
                shipping_city,
                shipping_state,
                shipping_country,
                shipping_pincode_zip
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            customer_name,
            company_name,
            phone_number,
            email_address,
            gst_number,
            pan_number,

            data.get("street_address"),
            data.get("city"),
            data.get("state"),
            data.get("country"),
            data.get("pincode_zip"),

            data.get(
                "shipping_street_address"
            ),
            data.get("shipping_city"),
            data.get("shipping_state"),
            data.get("shipping_country"),
            data.get(
                "shipping_pincode_zip"
            )
        ))

        customer_id = cur.fetchone()[0]

        customer_display_name = (
            company_name
            or customer_name
            or "Customer"
        )

        add_activity(
            activity_type="customer",
            action="created",
            title="New customer added",

            description=(
                f'Customer '
                f'"{customer_display_name}" '
                f'has been added'
            ),

            reference_id=customer_id,
            reference_number=None,

            user_id=actor_user_id,
            user_name=actor_user_name,

            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "Customer added successfully",

            "customer_id":
                customer_id
        }), 201

    except IntegrityError as error:
        conn.rollback()

        error_text = str(error).lower()

        if "email_address" in error_text:
            message = (
                "A customer with this email "
                "address already exists"
            )

        elif "gst_number" in error_text:
            message = (
                "A customer with this GST "
                "number already exists"
            )

        elif "phone" in error_text:
            message = (
                "A customer with this phone "
                "number already exists"
            )

        else:
            message = (
                "Customer details already exist"
            )

        return jsonify({
            "message": message,
            "error": str(error)
        }), 409

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error adding customer",

            "error":
                str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# GET ALL CUSTOMERS
@customer_bp.route("/customers", methods=["GET"])
def get_customers():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM customers
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append({
            "id": row[0],
            "customer_name": row[1],
            "company_name": row[2],
            "email_address": row[3],
            "phone_number": row[4],
            "gst_number": row[5],
            "pan_number": row[6],
            "street_address": row[7],
            "city": row[8],
            "state": row[9],
            "country": row[10],
            "pincode_zip": row[11],
            "shipping_street_address": row[12],
            "shipping_city": row[13],
            "shipping_state": row[14],
            "shipping_country": row[15],
            "shipping_pincode_zip": row[16]
        })

    cur.close()
    conn.close()

    return jsonify(result)


# GET SINGLE CUSTOMER
@customer_bp.route("/customer/<int:id>", methods=["GET"])
def get_customer(id):

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM customers
        WHERE id=%s
    """, (id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return jsonify({
            "message": "Customer Not Found"
        }), 404

    return jsonify({
        "id": row[0],
        "customer_name": row[1],
        "company_name": row[2],
        "email_address": row[3],
        "phone_number": row[4],
        "gst_number": row[5],
        "pan_number": row[6],
        "street_address": row[7],
        "city": row[8],
        "state": row[9],
        "country": row[10],
        "pincode_zip": row[11],
        "shipping_street_address": row[12],
        "shipping_city": row[13],
        "shipping_state": row[14],
        "shipping_country": row[15],
        "shipping_pincode_zip": row[16]
    })


# # UPDATE CUSTOMER

@customer_bp.route(
    "/customer/<int:id>",
    methods=["PUT"]
)
def update_customer(id):
    data = request.get_json(
        silent=True
    ) or {}

    actor_user_id = data.get(
        "actor_user_id"
    )

    actor_user_name = data.get(
        "actor_user_name"
    )

    customer_name = str(
        data.get("customer_name") or ""
    ).strip()

    company_name = str(
        data.get("company_name") or ""
    ).strip()

    email_address = normalize_email_address(
        data.get("email_address")
    )

    phone_number = normalize_phone_number(
        data.get("phone_number")
    )

    gst_number = normalize_gst_number(
        data.get("gst_number")
    )

    pan_number = str(
        data.get("pan_number") or ""
    ).strip().upper()

    # ---------------------------------------
    # Required field validation
    # ---------------------------------------

    if not customer_name:
        return jsonify({
            "message":
                "Customer name is required"
        }), 400

    if not company_name:
        return jsonify({
            "message":
                "Company name is required"
        }), 400

    if not email_address:
        return jsonify({
            "message":
                "Email address is required"
        }), 400

    if len(phone_number) != 10:
        return jsonify({
            "message":
                "Please enter a valid "
                "10-digit phone number"
        }), 400

    if len(gst_number) != 15:
        return jsonify({
            "message":
                "Please enter a valid "
                "15-character GST number"
        }), 400

    conn = pg_connection()
    cur = conn.cursor()

    try:
        # ---------------------------------------
        # Confirm customer exists and lock it
        # ---------------------------------------

        cur.execute("""
            SELECT
                id,
                customer_name,
                company_name

            FROM customers

            WHERE id = %s

            FOR UPDATE
        """, (
            id,
        ))

        existing_customer = cur.fetchone()

        if not existing_customer:
            return jsonify({
                "message":
                    "Customer not found"
            }), 404

        # ---------------------------------------
        # Check duplicate phone or GST
        # Exclude the current customer.
        # ---------------------------------------

        cur.execute("""
            SELECT
                id,
                customer_name,
                company_name,
                email_address,
                phone_number,
                gst_number

            FROM customers

            WHERE
                id <> %s

                AND (
                    CASE
                        WHEN LENGTH(
                            REGEXP_REPLACE(
                                phone_number,
                                '[^0-9]',
                                '',
                                'g'
                            )
                        ) = 12

                        AND REGEXP_REPLACE(
                            phone_number,
                            '[^0-9]',
                            '',
                            'g'
                        ) LIKE '91%%'

                        THEN RIGHT(
                            REGEXP_REPLACE(
                                phone_number,
                                '[^0-9]',
                                '',
                                'g'
                            ),
                            10
                        )

                        ELSE REGEXP_REPLACE(
                            phone_number,
                            '[^0-9]',
                            '',
                            'g'
                        )
                    END = %s

                    OR UPPER(
                        TRIM(gst_number)
                    ) = %s
                )

            LIMIT 1
        """, (
            id,
            phone_number,
            gst_number
        ))

        duplicate_customer = cur.fetchone()

        if duplicate_customer:
            existing_phone = (
                normalize_phone_number(
                    duplicate_customer[4]
                )
            )

            existing_gst = (
                normalize_gst_number(
                    duplicate_customer[5]
                )
            )

            same_phone = (
                existing_phone ==
                phone_number
            )

            same_gst = (
                existing_gst ==
                gst_number
            )

            if same_phone and same_gst:
                message = (
                    "Another customer already "
                    "has this phone number and "
                    "GST number"
                )

            elif same_phone:
                message = (
                    "Another customer already "
                    "has this phone number"
                )

            else:
                message = (
                    "Another customer already "
                    "has this GST number"
                )

            return jsonify({
                "message": message,

                "existing_customer_id":
                    duplicate_customer[0],

                "existing_customer_name":
                    duplicate_customer[1],

                "existing_company_name":
                    duplicate_customer[2]
            }), 409

        # ---------------------------------------
        # Check duplicate email
        # Exclude the current customer.
        # ---------------------------------------

        cur.execute("""
            SELECT
                id,
                customer_name,
                company_name

            FROM customers

            WHERE
                id <> %s

                AND LOWER(
                    TRIM(email_address)
                ) = %s

            LIMIT 1
        """, (
            id,
            email_address
        ))

        duplicate_email = cur.fetchone()

        if duplicate_email:
            return jsonify({
                "message":
                    "Another customer already "
                    "has this email address",

                "existing_customer_id":
                    duplicate_email[0],

                "existing_customer_name":
                    duplicate_email[1],

                "existing_company_name":
                    duplicate_email[2]
            }), 409

        # ---------------------------------------
        # Update customer
        # ---------------------------------------

        cur.execute("""
            UPDATE customers

            SET
                customer_name = %s,
                company_name = %s,
                email_address = %s,
                phone_number = %s,
                gst_number = %s,
                pan_number = %s,

                street_address = %s,
                city = %s,
                state = %s,
                country = %s,
                pincode_zip = %s,

                shipping_street_address = %s,
                shipping_city = %s,
                shipping_state = %s,
                shipping_country = %s,
                shipping_pincode_zip = %s

            WHERE id = %s

            RETURNING id
        """, (
            customer_name,
            company_name,
            email_address,
            phone_number,
            gst_number,
            pan_number,

            data.get("street_address"),
            data.get("city"),
            data.get("state"),
            data.get("country"),
            data.get("pincode_zip"),

            data.get(
                "shipping_street_address"
            ),
            data.get("shipping_city"),
            data.get("shipping_state"),
            data.get("shipping_country"),
            data.get(
                "shipping_pincode_zip"
            ),

            id
        ))

        updated_customer = cur.fetchone()

        if not updated_customer:
            conn.rollback()

            return jsonify({
                "message":
                    "Customer not found"
            }), 404

        customer_id = updated_customer[0]

        customer_display_name = (
            company_name
            or customer_name
            or "Customer"
        )

        add_activity(
            activity_type="customer",
            action="updated",
            title="Customer updated",

            description=(
                f'Customer '
                f'"{customer_display_name}" '
                f'has been updated'
            ),

            reference_id=customer_id,
            reference_number=None,

            user_id=actor_user_id,
            user_name=actor_user_name,

            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "Customer updated successfully",

            "customer_id":
                customer_id
        }), 200

    except IntegrityError as error:
        conn.rollback()

        error_text = str(error).lower()

        if "email_address" in error_text:
            message = (
                "Another customer already "
                "has this email address"
            )

        elif "gst_number" in error_text:
            message = (
                "Another customer already "
                "has this GST number"
            )

        elif "phone" in error_text:
            message = (
                "Another customer already "
                "has this phone number"
            )

        else:
            message = (
                "The updated customer details "
                "conflict with another customer"
            )

        return jsonify({
            "message": message,
            "error": str(error)
        }), 409

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error updating customer",

            "error":
                str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


# DELETE CUSTOMER
@customer_bp.route("/customer/<int:id>", methods=["DELETE"])
def delete_customer(id):

    conn = pg_connection()
    cur = conn.cursor()

    try:
        data = request.get_json() or {}

        actor_user_id = data.get("actor_user_id")
        actor_user_name = data.get("actor_user_name")

        cur.execute("""
            SELECT company_name, customer_name
            FROM customers
            WHERE id=%s
        """, (id,))

        customer = cur.fetchone()

        if not customer:
            return jsonify({"message": "Customer not found"}), 404

        customer_name = customer[0] or customer[1]

        add_activity(
            activity_type="customer",
            action="deleted",
            title="Customer Deleted",
            description=f'Customer "{customer_name}" has been deleted',
            reference_id=id,
            user_id=actor_user_id,
            user_name=actor_user_name,
            conn=conn
        )

        cur.execute("""
            DELETE FROM customers
            WHERE id=%s
        """, (id,))

        conn.commit()

        return jsonify({
            "message": "Customer Deleted Successfully"
        }), 200

    except Exception as e:
        conn.rollback()

        return jsonify({
            "message": "Error deleting customer",
            "error": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()