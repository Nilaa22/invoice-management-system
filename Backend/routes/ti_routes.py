
# =====================================
# CREATE TABLES
# =====================================

from flask import Blueprint, request, jsonify
from database_postgres import pg_connection

from psycopg2.extras import RealDictCursor

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, jsonify, request

from utils.amount_to_words import amount_to_words


utils_bp = Blueprint(
    "utils_bp",
    __name__
)


@utils_bp.route(
    "/amount-to-words",
    methods=["POST"]
)
def convert_amount():
    data = request.get_json(
        silent=True
    ) or {}

    raw_amount = data.get("amount")

    if raw_amount is None:
        return jsonify({
            "message": "Amount is required"
        }), 400

    try:
        amount = Decimal(
            str(raw_amount)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if amount < 0:
            return jsonify({
                "message": (
                    "Amount cannot be negative"
                )
            }), 400

        return jsonify({
            "amount": str(amount),
            "amount_in_words":
                amount_to_words(amount)
        }), 200

    except (
        InvalidOperation,
        TypeError,
        ValueError
    ):
        return jsonify({
            "message": "Invalid amount"
        }), 400

from routes.activity_routes import add_activity

ti_bp = Blueprint("ti_bp", __name__)


# CREATE TABLES (POSTGRESQL)

def ti():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
CREATE TABLE IF NOT EXISTS ti_bills (
    ti_id SERIAL PRIMARY KEY,
    ti_number VARCHAR(100) UNIQUE,

    customer_id VARCHAR(100),
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

    untaxed_amount NUMERIC(12,2),
    gst_amount NUMERIC(12,2),
    total_amount NUMERIC(12,2),
    terms TEXT,
    payment_terms TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ti_items (
            item_id SERIAL PRIMARY KEY,
            ti_id INTEGER REFERENCES ti_bills(ti_id) ON DELETE CASCADE,
            product_id INTEGER,
            product_name VARCHAR(255),
            description TEXT,
            quantity NUMERIC(10,2),
            unit_price NUMERIC(12,2),
            tax NUMERIC(5,2),
            tax_type VARCHAR(20),
            discount NUMERIC(5,2),
            total NUMERIC(12,2),
            hsn_sac_code  VARCHAR(100)
        )
    """)
    

    cur.execute(""" CREATE TABLE IF NOT EXISTS ti_payments (
    payment_id SERIAL PRIMARY KEY,
    ti_id INTEGER NOT NULL
        REFERENCES ti_bills(ti_id)
        ON DELETE CASCADE,

    payment_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    payment_mode VARCHAR(100) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) """)
            
    conn.commit()
    cur.close()
    conn.close()


@ti_bp.route("/ti", methods=["POST"])
def save_ti():
    data = request.get_json(
        silent=True
    ) or {}

    customer = data.get("customer") or {}
    items = data.get("items") or []

    actor_user_id = data.get(
        "actor_user_id"
    )

    actor_user_name = data.get(
        "actor_user_name"
    )

    source_pi_id = data.get(
        "source_pi_id"
    )

    source_pi_number = data.get(
        "source_pi_number"
    )

    conversion_mode = bool(
        data.get("conversionMode")
    )

    ti_number = data.get("ti_number")

    if not ti_number:
        return jsonify({
            "message":
                "Tax Invoice number is required"
        }), 400

    if not customer:
        return jsonify({
            "message":
                "Customer information is required"
        }), 400

    if not items:
        return jsonify({
            "message":
                "At least one product is required"
        }), 400

    if conversion_mode and not source_pi_id:
        return jsonify({
            "message":
                "Source PI ID is required "
                "for PI conversion"
        }), 400

    conn = pg_connection()
    cur = conn.cursor()

    try:
        total_amount = Decimal(
            str(
                data.get(
                    "total_amount",
                    0
                )
            )
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        generated_amount_in_words = (
            amount_to_words(total_amount)
        )

        # =============================================
        # LOCK AND VALIDATE SOURCE PI
        # =============================================

        if conversion_mode and source_pi_id:
            cur.execute("""
                SELECT
                    pi_id,
                    pi_number,
                    converted_to_ti,
                    ti_id,
                    ti_number

                FROM pi_bills

                WHERE pi_id = %s

                FOR UPDATE
            """, (
                source_pi_id,
            ))

            pi_record = cur.fetchone()

            if not pi_record:
                conn.rollback()

                return jsonify({
                    "message":
                        "Source PI not found"
                }), 404

            database_pi_id = pi_record[0]
            database_pi_number = pi_record[1]
            already_converted = bool(
                pi_record[2]
            )

            existing_ti_id = pi_record[3]
            existing_ti_number = pi_record[4]

            if already_converted:
                conn.rollback()

                return jsonify({
                    "message": (
                        "This PI has already "
                        "been converted to "
                        f"{existing_ti_number or 'a Tax Invoice'}"
                    ),

                    "ti_id":
                        existing_ti_id,

                    "ti_number":
                        existing_ti_number
                }), 409

            if (
                source_pi_number
                and database_pi_number
                != source_pi_number
            ):
                conn.rollback()

                return jsonify({
                    "message":
                        "Source PI number does "
                        "not match the PI ID"
                }), 400

        # =============================================
        # INSERT TAX INVOICE
        # =============================================

        cur.execute("""
            INSERT INTO ti_bills (
                ti_number,

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

                untaxed_amount,
                gst_amount,
                total_amount,
                amount_in_words,
                balance_amount,
                status,

                terms,
                payment_terms,

                pi_id,
                pi_number
            )
            VALUES (
                %s,

                %s, %s, %s, %s, %s, %s,

                %s, %s, %s, %s, %s,

                %s, %s, %s, %s, %s,

                %s,

                %s, %s, %s, %s, %s, %s,

                %s, %s,

                %s, %s
            )
            RETURNING ti_id
        """, (
            ti_number,

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

            customer.get(
                "shipping_street_address"
            ),
            customer.get("shipping_city"),
            customer.get("shipping_state"),
            customer.get("shipping_country"),
            customer.get(
                "shipping_pincode_zip"
            ),

            data.get("quotation_date"),

            data.get("untaxed_amount", 0),
            data.get("gst_amount", 0),
            total_amount,
            generated_amount_in_words,
            total_amount,
            "Unpaid",

            data.get("terms"),
            data.get("payment_terms"),

            source_pi_id,
            source_pi_number
        ))

        ti_id = cur.fetchone()[0]

        # =============================================
        # INSERT TAX INVOICE PRODUCTS
        # =============================================

        for item in items:
            cur.execute("""
                INSERT INTO ti_items (
                    ti_id,
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
            """, (
                ti_id,

                item.get("product_id"),
                item.get("product_name"),
                item.get("description"),

                item.get("quantity", 0),
                item.get("unit_price", 0),

                item.get("hsn_sac_code"),

                item.get("tax", 0),
                item.get("tax_type"),

                item.get("discount", 0),
                item.get("total", 0)
            ))

        # =============================================
        # UPDATE ORIGINAL PI
        # =============================================

        if conversion_mode and source_pi_id:
            cur.execute("""
                UPDATE pi_bills

                SET
                    converted_to_ti = TRUE,
                    ti_id = %s,
                    ti_number = %s

                WHERE
                    pi_id = %s
                    AND COALESCE(
                        converted_to_ti,
                        FALSE
                    ) = FALSE
            """, (
                ti_id,
                ti_number,
                source_pi_id
            ))

            if cur.rowcount != 1:
                raise Exception(
                    "Source PI could not be "
                    "updated after TI creation"
                )

        add_activity(
            activity_type="ti",
            action="created",

            title=(
                "New Tax Invoice created"
            ),

            description=(
                f"{ti_number} has been created"
                + (
                    f" from {source_pi_number}"
                    if source_pi_number
                    else ""
                )
            ),

            reference_id=ti_id,
            reference_number=ti_number,

            user_id=actor_user_id,
            user_name=actor_user_name,

            conn=conn
        )

        cur.execute("""
            UPDATE company

            SET ti_start_no =
                ti_start_no + 1

            WHERE company_id = 1
        """)

        conn.commit()

        return jsonify({
            "message":
                "Tax Invoice saved successfully",

            "ti_id":
                ti_id,

            "ti_number":
                ti_number,

            "source_pi_id":
                source_pi_id,

            "source_pi_number":
                source_pi_number,

            "converted_to_ti":
                bool(
                    conversion_mode
                    and source_pi_id
                )
        }), 201

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error saving Tax Invoice",

            "error":
                str(error)
        }), 500

    finally:
        cur.close()
        conn.close()


@ti_bp.route(
    "/tax-invoices",
    methods=["GET"]
)
def get_tax_invoices():
    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        cur.execute("""
            SELECT
                ti_id,
                ti_number,

                customer_id,
                customer_name,
                company_name,

                quotation_date,
                total_amount,

                COALESCE(
                    balance_amount,
                    total_amount
                ) AS balance_amount,

                COALESCE(
                    status,
                    'Unpaid'
                ) AS status,

                pi_id,
                pi_number

            FROM ti_bills

            ORDER BY
                quotation_date DESC,
                ti_id DESC
        """)

        invoice_rows = cur.fetchall()

        invoices = []

        for invoice in invoice_rows:
            cur.execute("""
                SELECT
                    item_id,
                    product_id,
                    product_name,
                    description,
                    hsn_sac_code,
                    quantity,
                    unit_price,
                    tax,
                    tax_type,
                    discount,
                    total

                FROM ti_items

                WHERE ti_id = %s

                ORDER BY item_id
            """, (
                invoice["ti_id"],
            ))

            product_rows = cur.fetchall()

            products = []

            for product in product_rows:
                products.append({
                    "item_id":
                        product["item_id"],

                    "product_id":
                        product["product_id"],

                    "product_name":
                        product["product_name"]
                        or "",

                    "description":
                        product["description"]
                        or "",

                    "hsn_sac_code":
                        product["hsn_sac_code"]
                        or "",

                    "quantity":
                        float(
                            product["quantity"]
                            or 0
                        ),

                    "unit_price":
                        float(
                            product["unit_price"]
                            or 0
                        ),

                    "tax":
                        float(
                            product["tax"]
                            or 0
                        ),

                    "tax_type":
                        product["tax_type"]
                        or "",

                    "discount":
                        float(
                            product["discount"]
                            or 0
                        ),

                    "total":
                        float(
                            product["total"]
                            or 0
                        )
                })

            cur.execute("""
                SELECT
                    payment_id,
                    payment_date,
                    amount,
                    payment_mode,
                    reference_id

                FROM ti_payments

                WHERE ti_id = %s

                ORDER BY
                    payment_date DESC,
                    payment_id DESC
            """, (
                invoice["ti_id"],
            ))

            payment_rows = cur.fetchall()

            payments = []

            for payment in payment_rows:
                payments.append({
                    "payment_id":
                        payment["payment_id"],

                    "payment_date": (
                        payment[
                            "payment_date"
                        ].strftime(
                            "%Y-%m-%d"
                        )
                        if payment[
                            "payment_date"
                        ]
                        else ""
                    ),

                    "amount":
                        float(
                            payment["amount"]
                            or 0
                        ),

                    "payment_mode":
                        payment[
                            "payment_mode"
                        ] or "",

                    "reference_id":
                        payment[
                            "reference_id"
                        ] or ""
                })

            invoices.append({
                "ti_id":
                    invoice["ti_id"],

                "ti_number":
                    invoice["ti_number"],

                "customer_id":
                    invoice["customer_id"],

                "customer_name":
                    invoice["customer_name"]
                    or "",

                "company_name":
                    invoice["company_name"]
                    or "",

                "invoice_date": (
                    invoice[
                        "quotation_date"
                    ].strftime(
                        "%Y-%m-%d"
                    )
                    if invoice[
                        "quotation_date"
                    ]
                    else ""
                ),

                "total_amount":
                    float(
                        invoice[
                            "total_amount"
                        ] or 0
                    ),

                "balance_amount":
                    float(
                        invoice[
                            "balance_amount"
                        ] or 0
                    ),

                "status":
                    invoice["status"]
                    or "Unpaid",

                # Existing TI database reference
                # to the original PI.
                "pi_id":
                    invoice["pi_id"],

                "pi_number":
                    invoice["pi_number"]
                    or "",

                # These aliases match the names
                # already used by TI_Generation
                # and TI_Structure.
                "source_pi_id":
                    invoice["pi_id"],

                "source_pi_number":
                    invoice["pi_number"]
                    or "",

                "conversionMode":
                    bool(
                        invoice["pi_id"]
                    ),

                "products":
                    products,

                "payments":
                    payments
            })

        return jsonify(invoices), 200

    except Exception as error:
        return jsonify({
            "message":
                "Error fetching Tax Invoices",

            "error":
                str(error)
        }), 500

    finally:
        cur.close()
        conn.close()
        
                
# @ti_bp.route("/ti/<int:ti_id>", methods=["GET"])
# def get_single_ti(ti_id):
#     conn = pg_connection()
#     cur = conn.cursor()

#     try:
#         cur.execute("""
#             SELECT *
#             FROM ti_bills
#             WHERE ti_id = %s
#         """, (ti_id,))

#         bill = cur.fetchone()

#         if bill is None:
#             return jsonify({"message": "Tax Invoice not found"}), 404

#         cur.execute("""
#             SELECT
#                 product_id,
#                 product_name,
#                 description,
#                 hsn_sac_code,
#                 quantity,
#                 unit_price,
#                 tax,
#                 tax_type,
#                 discount,
#                 total
#             FROM ti_items
#             WHERE ti_id = %s
#             ORDER BY item_id
#         """, (ti_id,))

#         items = cur.fetchall()

#         return jsonify({
#             "ti_id": bill[0],
#             "ti_number": bill[1],
#             "customer": {
#                 "id": bill[2],
#                 "customer_name": bill[3],
#                 "company_name": bill[4],
#                 "gst_number": bill[5],
#                 "phone_number": bill[6],
#                 "email_address": bill[7],
#                 "street_address": bill[8],
#                 "city": bill[9],
#                 "state": bill[10],
#                 "country": bill[11],
#                 "pincode_zip": bill[12],
#                 "shipping_street_address": bill[13],
#                 "shipping_city": bill[14],
#                 "shipping_state": bill[15],
#                 "shipping_country": bill[16],
#                 "shipping_pincode_zip": bill[17]
#             },
#             "issueDate": bill[18].strftime("%Y-%m-%d") if bill[18] else "",
#             # "expiryDate": bill[19].strftime("%Y-%m-%d") if bill[19] else "",
#             "untaxed": float(bill[20] or 0),
#             "taxed": float(bill[21] or 0),
#             "grandTotal": float(bill[22] or 0),
#             "terms": bill[23],
#             "payment_terms": bill[24],
#             "amount_in_words":bill[30],
#             "products": [
#                 {
#                     "product_id": item[0],
#                     "product_name": item[1],
#                     "description": item[2],
#                     "hsn_sac_code": item[3],
#                     "quantity": float(item[4] or 0),
#                     "unit_price": float(item[5] or 0),
#                     "tax": float(item[6] or 0),
#                     "tax_type": item[7],
#                     "discount": float(item[8] or 0),
#                     "total": float(item[9] or 0)
#                 }
#                 for item in items
#             ]
#         }), 200

#     except Exception as e:
#         return jsonify({
#             "message": "Error fetching tax invoice",
#             "error": str(e)
#         }), 500

#     finally:
#         cur.close()
#         conn.close()

@ti_bp.route(
    "/ti/<int:ti_id>",
    methods=["GET"]
)
def get_single_ti(ti_id):
    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        # Never use SELECT * here.
        # The database schema has changed over time,
        # so explicit column names prevent index errors.
        cur.execute("""
            SELECT
                ti_id,
                ti_number,

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

                untaxed_amount,
                gst_amount,
                total_amount,

                terms,
                payment_terms,
                amount_in_words,

                balance_amount,
                status,

                pi_id,
                pi_number

            FROM ti_bills

            WHERE ti_id = %s
        """, (
            ti_id,
        ))

        bill = cur.fetchone()

        if not bill:
            return jsonify({
                "message":
                    "Tax Invoice not found"
            }), 404

        cur.execute("""
            SELECT
                item_id,
                product_id,
                product_name,
                description,
                hsn_sac_code,
                quantity,
                unit_price,
                tax,
                tax_type,
                discount,
                total

            FROM ti_items

            WHERE ti_id = %s

            ORDER BY item_id
        """, (
            ti_id,
        ))

        item_rows = cur.fetchall()

        products = []

        for item in item_rows:
            products.append({
                "item_id":
                    item["item_id"],

                "product_id":
                    item["product_id"],

                "product_name":
                    item["product_name"]
                    or "",

                "description":
                    item["description"]
                    or "",

                "hsn_sac_code":
                    item["hsn_sac_code"]
                    or "",

                "quantity":
                    float(
                        item["quantity"]
                        or 0
                    ),

                "unit_price":
                    float(
                        item["unit_price"]
                        or 0
                    ),

                "tax":
                    float(
                        item["tax"]
                        or 0
                    ),

                "tax_type":
                    item["tax_type"]
                    or "",

                "discount":
                    float(
                        item["discount"]
                        or 0
                    ),

                "total":
                    float(
                        item["total"]
                        or 0
                    )
            })

        return jsonify({
            "ti_id":
                bill["ti_id"],

            "ti_number":
                bill["ti_number"]
                or "",

            "customer": {
                "id":
                    bill["customer_id"],

                "customer_id":
                    bill["customer_id"],

                "customer_name":
                    bill["customer_name"]
                    or "",

                "company_name":
                    bill["company_name"]
                    or "",

                "gst_number":
                    bill["gst_number"]
                    or "",

                "phone_number":
                    bill["phone_number"]
                    or "",

                "email_address":
                    bill["email_address"]
                    or "",

                "street_address":
                    bill["street_address"]
                    or "",

                "city":
                    bill["city"]
                    or "",

                "state":
                    bill["state"]
                    or "",

                "country":
                    bill["country"]
                    or "",

                "pincode_zip":
                    bill["pincode_zip"]
                    or "",

                "shipping_street_address":
                    bill[
                        "shipping_street_address"
                    ] or "",

                "shipping_city":
                    bill["shipping_city"]
                    or "",

                "shipping_state":
                    bill["shipping_state"]
                    or "",

                "shipping_country":
                    bill["shipping_country"]
                    or "",

                "shipping_pincode_zip":
                    bill[
                        "shipping_pincode_zip"
                    ] or ""
            },

            "issueDate": (
                bill["quotation_date"].strftime(
                    "%Y-%m-%d"
                )
                if bill["quotation_date"]
                else ""
            ),

            "untaxed":
                float(
                    bill["untaxed_amount"]
                    or 0
                ),

            "taxed":
                float(
                    bill["gst_amount"]
                    or 0
                ),

            "grandTotal":
                float(
                    bill["total_amount"]
                    or 0
                ),

            "terms":
                bill["terms"]
                or "",

            "payment_terms":
                bill["payment_terms"]
                or "",

            "amount_in_words":
                bill["amount_in_words"]
                or "",

            "balance_amount":
                float(
                    bill["balance_amount"]
                    if bill["balance_amount"]
                    is not None
                    else bill["total_amount"]
                    or 0
                ),

            "status":
                bill["status"]
                or "Unpaid",

            "source_pi_id":
                bill["pi_id"],

            "source_pi_number":
                bill["pi_number"]
                or "",

            "pi_id":
                bill["pi_id"],

            "pi_number":
                bill["pi_number"]
                or "",

            "conversionMode":
                bool(
                    bill["pi_id"]
                ),

            "products":
                products
        }), 200

    except Exception as error:
        return jsonify({
            "message":
                "Error fetching tax invoice",

            "error":
                str(error)
        }), 500

    finally:
        cur.close()
        conn.close()
        


@ti_bp.route("/ti/<int:ti_id>", methods=["PUT"])
def update_ti(ti_id):
    data = request.get_json(
        silent=True
    ) or {}

    customer = data.get("customer") or {}
    items = data.get("items") or []

    actor_user_id = data.get(
        "actor_user_id"
    )

    actor_user_name = data.get(
        "actor_user_name"
    )

    source_pi_id = data.get(
        "source_pi_id"
    )

    source_pi_number = data.get(
        "source_pi_number"
    )

    conversion_mode = bool(
        data.get("conversionMode")
    )

    conn = pg_connection()
    cur = conn.cursor()

    try:
        # ---------------------------------------
        # Validate TI
        # ---------------------------------------

        cur.execute("""
            SELECT
                ti_id,
                ti_number,
                total_amount,
                balance_amount,
                pi_id,
                pi_number

            FROM ti_bills

            WHERE ti_id = %s

            FOR UPDATE
        """, (
            ti_id,
        ))

        existing_ti = cur.fetchone()

        if not existing_ti:
            return jsonify({
                "message":
                    "Tax Invoice not found"
            }), 404

        existing_pi_id = existing_ti[4]
        existing_pi_number = existing_ti[5]

        # Preserve the existing PI reference when
        # React does not send it while editing.
        if source_pi_id is None:
            source_pi_id = existing_pi_id

        if not source_pi_number:
            source_pi_number = (
                existing_pi_number
            )

        # ---------------------------------------
        # New total and amount in words
        # ---------------------------------------

        new_total_amount = Decimal(
            str(
                data.get(
                    "total_amount",
                    0
                )
            )
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if new_total_amount < 0:
            return jsonify({
                "message":
                    "Total amount cannot be negative"
            }), 400

        generated_amount_in_words = (
            amount_to_words(
                new_total_amount
            )
        )

        # ---------------------------------------
        # Find total payment already received
        # ---------------------------------------

        cur.execute("""
            SELECT
                COALESCE(
                    SUM(amount),
                    0
                )

            FROM ti_payments

            WHERE ti_id = %s
        """, (
            ti_id,
        ))

        paid_amount = Decimal(
            str(
                cur.fetchone()[0] or 0
            )
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # ---------------------------------------
        # Calculate new balance and status
        # ---------------------------------------

        new_balance_amount = (
            new_total_amount -
            paid_amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if new_balance_amount <= 0:
            new_balance_amount = Decimal(
                "0.00"
            )

            new_status = "Paid"

        elif paid_amount > 0:
            new_status = "Partial"

        else:
            new_status = "Unpaid"

        # ---------------------------------------
        # Update TI bill
        # ---------------------------------------

        cur.execute("""
            UPDATE ti_bills

            SET
                ti_number = %s,

                customer_id = %s,
                customer_name = %s,
                company_name = %s,
                gst_number = %s,
                phone_number = %s,
                email_address = %s,

                street_address = %s,
                city = %s,
                state = %s,
                country = %s,
                pincode_zip = %s,

                shipping_street_address = %s,
                shipping_city = %s,
                shipping_state = %s,
                shipping_country = %s,
                shipping_pincode_zip = %s,

                quotation_date = %s,

                untaxed_amount = %s,
                gst_amount = %s,
                total_amount = %s,
                balance_amount = %s,
                status = %s,
                amount_in_words = %s,

                terms = %s,
                payment_terms = %s,

                pi_id = %s,
                pi_number = %s

            WHERE ti_id = %s
        """, (
            data.get("ti_number"),

            data.get("customer_id"),
            customer.get(
                "customer_name"
            ),
            customer.get(
                "company_name"
            ),
            customer.get(
                "gst_number"
            ),
            customer.get(
                "phone_number"
            ),
            customer.get(
                "email_address"
            ),

            customer.get(
                "street_address"
            ),
            customer.get("city"),
            customer.get("state"),
            customer.get("country"),
            customer.get(
                "pincode_zip"
            ),

            customer.get(
                "shipping_street_address"
            ),
            customer.get(
                "shipping_city"
            ),
            customer.get(
                "shipping_state"
            ),
            customer.get(
                "shipping_country"
            ),
            customer.get(
                "shipping_pincode_zip"
            ),

            data.get(
                "quotation_date"
            ),

            data.get(
                "untaxed_amount",
                0
            ),
            data.get(
                "gst_amount",
                0
            ),

            new_total_amount,
            new_balance_amount,
            new_status,

            generated_amount_in_words,

            data.get("terms"),
            data.get(
                "payment_terms"
            ),

            source_pi_id,
            source_pi_number,

            ti_id
        ))

        # ---------------------------------------
        # Replace TI items
        # ---------------------------------------

        cur.execute("""
            DELETE FROM ti_items
            WHERE ti_id = %s
        """, (
            ti_id,
        ))

        for item in items:
            cur.execute("""
                INSERT INTO ti_items (
                    ti_id,
                    product_id,
                    product_name,
                    description,
                    hsn_sac_code,
                    quantity,
                    unit_price,
                    tax,
                    tax_type,
                    discount,
                    total
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                ti_id,

                item.get(
                    "product_id"
                ),

                item.get(
                    "product_name"
                ),

                item.get(
                    "description"
                ),

                item.get(
                    "hsn_sac_code"
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
                    "tax",
                    0
                ),

                item.get(
                    "tax_type"
                ),

                item.get(
                    "discount",
                    0
                ),

                item.get(
                    "total",
                    0
                )
            ))

        # ---------------------------------------
        # Ensure linked PI still points to this TI
        # ---------------------------------------

        if source_pi_id:
            cur.execute("""
                UPDATE pi_bills

                SET
                    converted_to_ti = TRUE,
                    ti_id = %s,
                    ti_number = %s

                WHERE pi_id = %s
            """, (
                ti_id,
                data.get("ti_number"),
                source_pi_id
            ))

        # ---------------------------------------
        # Activity log
        # ---------------------------------------

        add_activity(
            activity_type="ti",
            action="updated",

            title=(
                "Tax Invoice updated"
            ),

            description=(
                f'{data.get("ti_number")} '
                f'has been updated. '
                f'New total: '
                f'₹{new_total_amount:,.2f}, '
                f'Balance: '
                f'₹{new_balance_amount:,.2f}'
            ),

            reference_id=ti_id,

            reference_number=data.get(
                "ti_number"
            ),

            user_id=actor_user_id,
            user_name=actor_user_name,

            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "TI updated successfully",

            "ti_id":
                ti_id,

            "ti_number":
                data.get("ti_number"),

            "source_pi_id":
                source_pi_id,

            "source_pi_number":
                source_pi_number,

            "conversionMode":
                conversion_mode,

            "total_amount":
                str(new_total_amount),

            "paid_amount":
                str(paid_amount),

            "balance_amount":
                str(
                    new_balance_amount
                ),

            "status":
                new_status,

            "amount_in_words":
                generated_amount_in_words
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error updating TI",

            "error":
                str(error)
        }), 500

    finally:
        cur.close()
        conn.close()





@ti_bp.route(
    "/ti-payments",
    methods=["POST"]
)
def record_ti_payment():
    data = request.get_json(
        silent=True
    ) or {}

    ti_id = data.get("ti_id")

    ti_number = str(
        data.get("ti_number", "")
    ).strip()

    payment_mode = str(
        data.get("payment_mode", "")
    ).strip()

    payment_date = data.get(
        "payment_date"
    )

    reference_id = str(
        data.get("reference_id", "")
    ).strip()

    actor_user_id = data.get(
        "actor_user_id"
    )

    actor_user_name = data.get(
        "actor_user_name"
    )

    if not ti_id:
        return jsonify({
            "message":
                "Tax Invoice ID is required"
        }), 400

    if not payment_mode:
        return jsonify({
            "message":
                "Payment method is required"
        }), 400

    if not payment_date:
        return jsonify({
            "message":
                "Payment date is required"
        }), 400

    try:
        amount = Decimal(
            str(data.get("amount", 0))
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError
    ):
        return jsonify({
            "message":
                "Invalid payment amount"
        }), 400

    if amount <= 0:
        return jsonify({
            "message":
                "Payment must be greater than zero"
        }), 400

    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        # Lock invoice before changing balance.
        cur.execute("""
            SELECT
                ti_id,
                ti_number,
                total_amount,
                balance_amount,
                status
            FROM ti_bills
            WHERE ti_id = %s
            FOR UPDATE
        """, (ti_id,))

        invoice = cur.fetchone()

        if not invoice:
            return jsonify({
                "message":
                    "Tax Invoice not found"
            }), 404

        current_balance = Decimal(
            str(
                invoice["balance_amount"]
                if invoice["balance_amount"]
                is not None
                else invoice["total_amount"]
            )
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if current_balance <= 0:
            return jsonify({
                "message":
                    "This Tax Invoice is already paid"
            }), 400

        if amount > current_balance:
            return jsonify({
                "message": (
                    "Payment cannot exceed "
                    "the pending balance"
                ),
                "pending_balance":
                    str(current_balance)
            }), 400

        new_balance = (
            current_balance - amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if new_balance == Decimal("0.00"):
            new_status = "Paid"
        else:
            new_status = "Partial"

        cur.execute("""
            INSERT INTO ti_payments (
                ti_id,
                payment_date,
                amount,
                payment_mode,
                reference_id
            )
            VALUES (
                %s, %s, %s, %s, %s
            )
            RETURNING payment_id
        """, (
            ti_id,
            payment_date,
            amount,
            payment_mode,
            reference_id or None
        ))

        payment = cur.fetchone()

        payment_id = payment[
            "payment_id"
        ]

        cur.execute("""
            UPDATE ti_bills
            SET
                balance_amount = %s,
                status = %s
            WHERE ti_id = %s
        """, (
            new_balance,
            new_status,
            ti_id
        ))

        actual_ti_number = (
            invoice["ti_number"]
            or ti_number
        )

        add_activity(
            activity_type="payment",
            action="created",

            title=(
                "Full payment received"
                if new_status == "Paid"
                else "Partial payment received"
            ),

            description=(
                f'Payment of ₹{amount:,.2f} '
                f'recorded for '
                f'{actual_ti_number}. '
                f'Balance: '
                f'₹{new_balance:,.2f}'
                + (
                    f'. Reference: '
                    f'{reference_id}'
                    if reference_id
                    else ""
                )
            ),

            reference_id=payment_id,

            reference_number=
                actual_ti_number,

            user_id=actor_user_id,
            user_name=actor_user_name,

            conn=conn
        )

        conn.commit()

        return jsonify({
            "message":
                "Payment recorded successfully",

            "payment_id":
                payment_id,

            "ti_id":
                ti_id,

            "ti_number":
                actual_ti_number,

            "payment_amount":
                str(amount),

            "balance_amount":
                str(new_balance),

            "status":
                new_status,

            "reference_id":
                reference_id
        }), 201

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error recording payment",

            "error":
                str(error)
        }), 500

    finally:
        cur.close()
        conn.close()