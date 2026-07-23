
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from database_postgres import pg_connection
from routes.activity_routes import add_activity
from utils.amount_to_words import amount_to_words


pi_bp = Blueprint("pi_bp", __name__)


# =========================================================
# JSON SERIALIZATION HELPERS
# =========================================================

def serialize_value(value):
    # """
    # Convert PostgreSQL values into JSON-safe values.
    # """

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")

    return value


def serialize_row(row):
    return {
        key: serialize_value(value)
        for key, value in dict(row).items()
    }


def build_customer_object(pi):
    """
    Customer details are stored directly in pi_bills.
    This creates the customer object expected by React.
    """

    return {
        "id": pi.get("customer_id"),
        "customer_id": pi.get("customer_id"),

        "customer_name":
            pi.get("customer_name") or "",

        "company_name":
            pi.get("company_name") or "",

        "gst_number":
            pi.get("gst_number") or "",

        "phone_number":
            pi.get("phone_number") or "",

        "email_address":
            pi.get("email_address") or "",

        "street_address":
            pi.get("street_address") or "",

        "city":
            pi.get("city") or "",

        "state":
            pi.get("state") or "",

        "country":
            pi.get("country") or "",

        "pincode_zip":
            pi.get("pincode_zip") or "",

        "shipping_street_address":
            pi.get("shipping_street_address") or "",

        "shipping_city":
            pi.get("shipping_city") or "",

        "shipping_state":
            pi.get("shipping_state") or "",

        "shipping_country":
            pi.get("shipping_country") or "",

        "shipping_pincode_zip":
            pi.get("shipping_pincode_zip") or ""
    }


def fetch_pi_items(cursor, pi_id):
    """
    Fetch all products belonging to one PI.
    """

    cursor.execute("""
        SELECT
            item_id,
            pi_id,
            product_id,
            product_name,
            description,
            quantity,
            unit_price,
            tax,
            tax_type,
            discount,
            total,
            hsn_sac_code

        FROM pi_items

        WHERE pi_id = %s

        ORDER BY item_id
    """, (pi_id,))

    item_rows = cursor.fetchall()

    return [
        serialize_row(item)
        for item in item_rows
    ]


# =========================================================
# CREATE TABLES
# =========================================================

def pi():
    conn = pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pi_bills (
                pi_id SERIAL PRIMARY KEY,

                pi_number VARCHAR(100) UNIQUE NOT NULL,

                customer_id INTEGER,
                customer_name VARCHAR(255),
                company_name VARCHAR(255),
                gst_number VARCHAR(50),
                phone_number VARCHAR(50),
                email_address VARCHAR(255),

                street_address TEXT,
                city VARCHAR(100),
                state VARCHAR(100),
                country VARCHAR(100),
                pincode_zip VARCHAR(20),

                shipping_street_address TEXT,
                shipping_city VARCHAR(100),
                shipping_state VARCHAR(100),
                shipping_country VARCHAR(100),
                shipping_pincode_zip VARCHAR(20),

                quotation_date DATE,
                expiry_date DATE,

                untaxed_amount NUMERIC(12, 2),
                gst_amount NUMERIC(12, 2),
                total_amount NUMERIC(12, 2),

                amount_in_words TEXT,

                terms TEXT,
                payment_terms TEXT,

                converted_to_ti BOOLEAN DEFAULT FALSE,
                ti_id INTEGER,
                ti_number VARCHAR(100),

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pi_items (
                item_id SERIAL PRIMARY KEY,

                pi_id INTEGER
                    REFERENCES pi_bills(pi_id)
                    ON DELETE CASCADE,

                product_id INTEGER,
                product_name VARCHAR(255),
                description TEXT,

                quantity NUMERIC(10, 2),
                unit_price NUMERIC(12, 2),

                tax NUMERIC(5, 2),
                tax_type VARCHAR(20),

                discount NUMERIC(5, 2),
                total NUMERIC(12, 2),

                hsn_sac_code VARCHAR(100)
            )
        """)

        # /*
        #  * CREATE TABLE IF NOT EXISTS does not add missing
        #  * columns to an already existing table.
        #  *
        #  * These ALTER commands safely add them.
        #  */

        cur.execute("""
            ALTER TABLE pi_bills
            ADD COLUMN IF NOT EXISTS
                amount_in_words TEXT
        """)

        cur.execute("""
            ALTER TABLE pi_bills
            ADD COLUMN IF NOT EXISTS
                converted_to_ti BOOLEAN DEFAULT FALSE
        """)

        cur.execute("""
            ALTER TABLE pi_bills
            ADD COLUMN IF NOT EXISTS
                ti_id INTEGER
        """)

        cur.execute("""
            ALTER TABLE pi_bills
            ADD COLUMN IF NOT EXISTS
                ti_number VARCHAR(100)
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

# SAVE PI
@pi_bp.route("/pi", methods=["POST"])
def save_pi():
    data = request.get_json(silent=True) or {}

    customer = data.get("customer") or {}
    items = data.get("items") or []

    actor_user_id = data.get("actor_user_id")
    actor_user_name = data.get("actor_user_name")

    if not data.get("pi_number"):
        return jsonify({
            "message": "PI number is required"
        }), 400

    if not data.get("customer_id"):
        return jsonify({
            "message": "Customer is required"
        }), 400

    if not items:
        return jsonify({
            "message": "At least one product is required"
        }), 400

    conn = pg_connection()
    cur = conn.cursor()

    try:
        total_amount = Decimal(
            str(data.get("total_amount", 0))
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        generated_amount_in_words = amount_to_words(
            total_amount
        )

        cur.execute("""
            INSERT INTO pi_bills (
                pi_number,

                customer_id,
                customer_name,
                company_name,
                gst_number,
                phone_number,
                email_address,

                street_address,
                city,
                state,
                country,
                pincode_zip,

                shipping_street_address,
                shipping_city,
                shipping_state,
                shipping_country,
                shipping_pincode_zip,

                quotation_date,
                expiry_date,

                untaxed_amount,
                gst_amount,
                total_amount,
                amount_in_words,

                terms,
                payment_terms,

                converted_to_ti
            )
            VALUES (
                %s,

                %s, %s, %s, %s, %s, %s,

                %s, %s, %s, %s, %s,

                %s, %s, %s, %s, %s,

                %s, %s,

                %s, %s, %s, %s,

                %s, %s,

                FALSE
            )
            RETURNING pi_id
        """, (
            data.get("pi_number"),

            data.get("customer_id"),
            customer.get("customer_name"),
            customer.get("company_name"),
            customer.get("gst_number"),
            customer.get("phone_number"),
            customer.get("email_address"),

            customer.get("street_address"),
            customer.get("city"),
            customer.get("state"),
            customer.get("country"),
            customer.get("pincode_zip"),

            customer.get("shipping_street_address"),
            customer.get("shipping_city"),
            customer.get("shipping_state"),
            customer.get("shipping_country"),
            customer.get("shipping_pincode_zip"),

            data.get("quotation_date"),
            data.get("expiry_date"),

            data.get("untaxed_amount", 0),
            data.get("gst_amount", 0),
            total_amount,
            generated_amount_in_words,

            data.get("terms"),
            data.get("payment_terms")
        ))

        pi_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                INSERT INTO pi_items (
                    pi_id,
                    product_id,
                    product_name,
                    description,
                    quantity,
                    unit_price,
                    tax,
                    tax_type,
                    discount,
                    total,
                    hsn_sac_code
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
            """, (
                pi_id,

                item.get("product_id"),
                item.get("product_name"),
                item.get("description"),

                item.get("quantity", 0),
                item.get("unit_price", 0),

                item.get("tax", 0),
                item.get("tax_type"),

                item.get("discount", 0),
                item.get("total", 0),

                item.get("hsn_sac_code")
            ))

        cur.execute("""
            UPDATE company
            SET pi_start_no =
                COALESCE(pi_start_no, 0) + 1
            WHERE company_id = 1
        """)

        add_activity(
            activity_type="pi",
            action="created",
            title="New Proforma Invoice created",

            description=(
                f'{data.get("pi_number")} '
                f'has been created'
            ),

            reference_id=pi_id,
            reference_number=data.get("pi_number"),

            user_id=actor_user_id,
            user_name=actor_user_name,

            conn=conn
        )

        conn.commit()

        return jsonify({
            "message": "PI saved successfully",
            "pi_id": pi_id,
            "pi_number": data.get("pi_number"),
            "amount_in_words":
                generated_amount_in_words
        }), 201

    except Exception as error:
        conn.rollback()

        error_message = str(error)

        if (
            "duplicate key" in error_message.lower()
            or "unique constraint" in error_message.lower()
        ):
            return jsonify({
                "message":
                    "Proforma Invoice number already exists",
                "error": error_message
            }), 409

        return jsonify({
            "message": "Error saving PI",
            "error": error_message
        }), 500

    finally:
        cur.close()
        conn.close()

# FETCH ALL PI
@pi_bp.route("/pi", methods=["GET"])
def get_all_pi():
    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT *
            FROM pi_bills
            ORDER BY
                created_at DESC,
                pi_id DESC
        """)

        pi_rows = cur.fetchall()

        bills = []

        for pi_row in pi_rows:
            bill = serialize_row(pi_row)

            products = fetch_pi_items(
                cur,
                bill["pi_id"]
            )

            bill["products"] = products
            bill["items"] = products

            bill["customer"] = (
                build_customer_object(bill)
            )

            bill["converted_to_ti"] = bool(
                bill.get("converted_to_ti", False)
            )

            bills.append(bill)

        return jsonify(bills), 200

    except Exception as error:
        return jsonify({
            "message": "Error fetching PI bills",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()
        
# FETCH SINGLE PI
@pi_bp.route("/pi/<int:pi_id>", methods=["GET"])
def get_single_pi(pi_id):
    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT *
            FROM pi_bills
            WHERE pi_id = %s
        """, (pi_id,))

        pi_row = cur.fetchone()

        if not pi_row:
            return jsonify({
                "message": "PI not found"
            }), 404

        pi = serialize_row(pi_row)

        products = fetch_pi_items(
            cur,
            pi_id
        )

        pi["products"] = products
        pi["items"] = products

        pi["customer"] = (
            build_customer_object(pi)
        )

        # Compatibility fields used by your existing React code
        pi["issue"] = (
            pi.get("quotation_date") or ""
        )

        pi["expiry"] = (
            pi.get("expiry_date") or ""
        )

        pi["untaxed"] = float(
            pi.get("untaxed_amount") or 0
        )

        pi["taxed"] = float(
            pi.get("gst_amount") or 0
        )

        pi["grandTotal"] = float(
            pi.get("total_amount") or 0
        )

        pi["converted_to_ti"] = bool(
            pi.get("converted_to_ti", False)
        )

        return jsonify(pi), 200

    except Exception as error:
        return jsonify({
            "message": "Error fetching PI details",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()
        
        
        # put pi_bill
@pi_bp.route(
    "/pi/<int:pi_id>",
    methods=["PUT"]
)
def update_pi(pi_id):
    conn = pg_connection()
    cur = conn.cursor()

    try:
        data = request.get_json(
            silent=True
        ) or {}

        customer_id = data.get(
            "customer_id"
        )

        customer = (
            data.get("customer") or {}
        )

        quotation_date = data.get(
            "quotation_date"
        )

        expiry_date = data.get(
            "expiry_date"
        )

        untaxed_amount = data.get(
            "untaxed_amount",
            0
        )

        gst_amount = data.get(
            "gst_amount",
            0
        )

        total_amount = data.get(
            "total_amount",
            0
        )

        items = data.get("items") or []

        payment_terms = data.get(
            "payment_terms",
            ""
        )

        terms = data.get(
            "terms",
            ""
        )

        pi_number = data.get(
            "pi_number"
        )

        amount_in_words = data.get(
            "amount_in_words",
            ""
        )

        actor_user_id = data.get(
            "actor_user_id"
        )

        actor_user_name = data.get(
            "actor_user_name"
        )

        if not customer_id:
            return jsonify({
                "message":
                    "Customer is required"
            }), 400

        if not quotation_date:
            return jsonify({
                "message":
                    "Quotation date is required"
            }), 400

        if not items:
            return jsonify({
                "message":
                    "At least one product is required"
            }), 400

        # Lock the PI while updating it
        cur.execute(
            """
            SELECT
                pi_id,
                pi_number,
                converted_to_ti
            FROM pi_bills
            WHERE pi_id = %s
            FOR UPDATE
            """,
            (pi_id,)
        )

        existing_pi = cur.fetchone()

        if not existing_pi:
            conn.rollback()

            return jsonify({
                "message": "PI not found"
            }), 404

        # Optional protection:
        # prevent editing after conversion to TI
        if existing_pi[2]:
            conn.rollback()

            return jsonify({
                "message":
                    "This PI has already been converted to a Tax Invoice and cannot be updated."
            }), 409

        cur.execute(
            """
            UPDATE pi_bills
            SET
                customer_id = %s,
                quotation_date = %s,
                expiry_date = %s,
                untaxed_amount = %s,
                gst_amount = %s,
                total_amount = %s,
                payment_terms = %s,
                terms = %s,
                pi_number = %s,
                amount_in_words = %s
            WHERE pi_id = %s
            """,
            (
                customer_id,
                quotation_date,
                expiry_date,
                untaxed_amount,
                gst_amount,
                total_amount,
                payment_terms,
                terms,
                pi_number,
                amount_in_words,
                pi_id
            )
        )

      
        cur.execute(
            """
            DELETE FROM pi_items
            WHERE pi_id = %s
            """,
            (pi_id,)
        )

        for item in items:
            cur.execute(
                """
                INSERT INTO pi_items (
                    pi_id,
                    product_id,
                    product_name,
                    description,
                    quantity,
                    unit_price,
                    hsn_sac_code,
                    tax,
                    tax_type,
                    discount,
                    total
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    pi_id,
                    item.get("product_id"),
                    item.get(
                        "product_name",
                        ""
                    ),
                    item.get(
                        "description",
                        ""
                    ),
                    item.get(
                        "quantity",
                        0
                    ),
                    item.get(
                        "unit_price",
                        0
                    ),
                    item.get(
                        "hsn_sac_code",
                        ""
                    ),
                    item.get("tax", 0),
                    item.get(
                        "tax_type",
                        ""
                    ),
                    item.get(
                        "discount",
                        0
                    ),
                    item.get("total", 0)
                )
            )

        # Keep this activity insert only if these
        # columns match your current activity_logs table.
        add_activity(
    activity_type="pi",
    action="updated",
    title="Proforma Invoice updated",
    description=f"{pi_number or existing_pi[1]} has been updated",
    reference_id=pi_id,
    reference_number=pi_number or existing_pi[1],
    user_id=actor_user_id,
    user_name=actor_user_name,
    conn=conn
)

        conn.commit()

        return jsonify({
            "message":
                "Proforma Invoice updated successfully",
            "pi_id": pi_id,
            "pi_number":
                pi_number or existing_pi[1]
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error updating Proforma Invoice",
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()