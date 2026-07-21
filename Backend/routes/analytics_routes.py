from datetime import date, datetime

from flask import Blueprint, jsonify, request
from database_postgres import pg_connection
from psycopg2.extras import RealDictCursor


analytics_bp = Blueprint(
    "analytics_bp",
    __name__
)


def parse_date(value, field_name):
    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        raise ValueError(
            f"{field_name} must be in YYYY-MM-DD format"
        )


@analytics_bp.route("/analytics", methods=["GET"])
def get_analytics():
    from_date_string = request.args.get("from_date")
    to_date_string = request.args.get("to_date")

    try:
        from_date = parse_date(
            from_date_string,
            "from_date"
        )

        to_date = parse_date(
            to_date_string,
            "to_date"
        )

    except ValueError as error:
        return jsonify({
            "message": str(error)
        }), 400

    if from_date and to_date and from_date > to_date:
        return jsonify({
            "message": (
                "From date cannot be after to date"
            )
        }), 400

    conn = pg_connection()
    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        date_conditions = []
        date_values = []

        if from_date:
            date_conditions.append(
                "tb.quotation_date >= %s"
            )
            date_values.append(from_date)

        if to_date:
            date_conditions.append(
                "tb.quotation_date <= %s"
            )
            date_values.append(to_date)

        where_clause = ""

        if date_conditions:
            where_clause = (
                "WHERE " +
                " AND ".join(date_conditions)
            )

        # --------------------------------------
        # Total sales and pending
        # --------------------------------------

        cur.execute(f"""
            SELECT
                COALESCE(
                    SUM(tb.total_amount),
                    0
                ) AS total_sales,

                COALESCE(
                    SUM(
                        COALESCE(
                            tb.balance_amount,
                            tb.total_amount
                        )
                    ),
                    0
                ) AS total_pending
            FROM ti_bills tb
            {where_clause}
        """, tuple(date_values))

        summary = cur.fetchone()

        total_sales = float(
            summary["total_sales"] or 0
        )

        total_pending = float(
            summary["total_pending"] or 0
        )

        # Total received is calculated from payments
        # belonging to filtered invoices.

        payment_conditions = []
        payment_values = []

        if from_date:
            payment_conditions.append(
                "tb.quotation_date >= %s"
            )
            payment_values.append(from_date)

        if to_date:
            payment_conditions.append(
                "tb.quotation_date <= %s"
            )
            payment_values.append(to_date)

        payment_where = ""

        if payment_conditions:
            payment_where = (
                "WHERE " +
                " AND ".join(payment_conditions)
            )

        cur.execute(f"""
            SELECT
                COALESCE(
                    SUM(tp.amount),
                    0
                ) AS total_received
            FROM ti_payments tp
            INNER JOIN ti_bills tb
                ON tb.ti_id = tp.ti_id
            {payment_where}
        """, tuple(payment_values))

        payment_summary = cur.fetchone()

        total_received = float(
            payment_summary["total_received"] or 0
        )

        # --------------------------------------
        # Pending customers
        # --------------------------------------

        pending_conditions = [
            """
            COALESCE(
                tb.balance_amount,
                tb.total_amount
            ) > 0
            """
        ]

        pending_values = []

        if from_date:
            pending_conditions.append(
                "tb.quotation_date >= %s"
            )
            pending_values.append(from_date)

        if to_date:
            pending_conditions.append(
                "tb.quotation_date <= %s"
            )
            pending_values.append(to_date)

        pending_where = (
            "WHERE " +
            " AND ".join(pending_conditions)
        )

        cur.execute(f"""
        SELECT
        tb.ti_id,
        tb.ti_number,
        tb.customer_name,
        tb.company_name,

        tb.quotation_date AS issue_date,

        COALESCE(
            tb.balance_amount,
            tb.total_amount
        ) AS total_due,

        GREATEST(
            CURRENT_DATE - tb.quotation_date,
            0
        ) AS due_days

        FROM ti_bills tb

        {pending_where}

        ORDER BY
        due_days DESC,
        total_due DESC
        """, tuple(pending_values))

        pending_rows = cur.fetchall()

        pending_customers = []

        for row in pending_rows:
            pending_customers.append({
            "ti_id":
            row["ti_id"],

            "ti_number":
            row["ti_number"],

            "customer_name":
            row["customer_name"],

            "company_name":
            row["company_name"],

            "issue_date": (
            row["issue_date"].strftime(
                "%Y-%m-%d"
            )
            if row["issue_date"]
            else ""
              ),

            "total_due": float(
            row["total_due"] or 0
             ),

                "due_days": int(
                row["due_days"] or 0
                )
            })

        # --------------------------------------
        # Customer-wise sales
        # --------------------------------------

        cur.execute(f"""
            SELECT
                COALESCE(
                    tb.customer_id::TEXT,
                    tb.company_name,
                    tb.customer_name
                ) AS customer_key,

                MAX(tb.customer_name)
                    AS customer_name,

                MAX(tb.company_name)
                    AS company_name,

                COUNT(tb.ti_id)
                    AS invoice_count,

                COALESCE(
                    SUM(tb.total_amount),
                    0
                ) AS total_sales

            FROM ti_bills tb

            {where_clause}

            GROUP BY
                COALESCE(
                    tb.customer_id::TEXT,
                    tb.company_name,
                    tb.customer_name
                )

            ORDER BY total_sales DESC
        """, tuple(date_values))

        customer_rows = cur.fetchall()

        customer_sales = []

        for row in customer_rows:
            customer_sales.append({
                "customer_key":
                    row["customer_key"],

                "customer_name":
                    row["customer_name"],

                "company_name":
                    row["company_name"],

                "invoice_count": int(
                    row["invoice_count"] or 0
                ),

                "total_sales": float(
                    row["total_sales"] or 0
                )
            })

        # --------------------------------------
        # GST summary
        # --------------------------------------

        gst_conditions = []
        gst_values = []

        if from_date:
            gst_conditions.append(
                "tb.quotation_date >= %s"
            )
            gst_values.append(from_date)

        if to_date:
            gst_conditions.append(
                "tb.quotation_date <= %s"
            )
            gst_values.append(to_date)

        gst_where = ""

        if gst_conditions:
            gst_where = (
                "WHERE " +
                " AND ".join(gst_conditions)
            )

        cur.execute(f"""
            SELECT
                COALESCE(
                    SUM(
                        CASE
                            WHEN UPPER(ti.tax_type)
                                = 'CGST'
                            THEN
                                (
                                    (
                                        ti.quantity *
                                        ti.unit_price
                                    )
                                    -
                                    (
                                        (
                                            ti.quantity *
                                            ti.unit_price
                                        )
                                        *
                                        COALESCE(
                                            ti.discount,
                                            0
                                        )
                                        / 100
                                    )
                                )
                                *
                                COALESCE(
                                    ti.tax,
                                    0
                                )
                                / 100
                            ELSE 0
                        END
                    ),
                    0
                ) AS cgst,

                COALESCE(
                    SUM(
                        CASE
                            WHEN UPPER(ti.tax_type)
                                = 'SGST'
                            THEN
                                (
                                    (
                                        ti.quantity *
                                        ti.unit_price
                                    )
                                    -
                                    (
                                        (
                                            ti.quantity *
                                            ti.unit_price
                                        )
                                        *
                                        COALESCE(
                                            ti.discount,
                                            0
                                        )
                                        / 100
                                    )
                                )
                                *
                                COALESCE(
                                    ti.tax,
                                    0
                                )
                                / 100
                            ELSE 0
                        END
                    ),
                    0
                ) AS sgst,

                COALESCE(
                    SUM(
                        CASE
                            WHEN UPPER(ti.tax_type)
                                = 'IGST'
                            THEN
                                (
                                    (
                                        ti.quantity *
                                        ti.unit_price
                                    )
                                    -
                                    (
                                        (
                                            ti.quantity *
                                            ti.unit_price
                                        )
                                        *
                                        COALESCE(
                                            ti.discount,
                                            0
                                        )
                                        / 100
                                    )
                                )
                                *
                                COALESCE(
                                    ti.tax,
                                    0
                                )
                                / 100
                            ELSE 0
                        END
                    ),
                    0
                ) AS igst

            FROM ti_items ti

            INNER JOIN ti_bills tb
                ON tb.ti_id = ti.ti_id

            {gst_where}
        """, tuple(gst_values))

        gst_row = cur.fetchone()

        cgst = float(gst_row["cgst"] or 0)
        sgst = float(gst_row["sgst"] or 0)
        igst = float(gst_row["igst"] or 0)

        total_gst = cgst + sgst + igst

        return jsonify({
            "from_date": (
                from_date.strftime("%Y-%m-%d")
                if from_date
                else None
            ),

            "to_date": (
                to_date.strftime("%Y-%m-%d")
                if to_date
                else None
            ),

            "total_sales": total_sales,
            "total_received": total_received,
            "total_pending": total_pending,

            "pending_customers":
                pending_customers,

            "customer_sales":
                customer_sales,

            "gst_summary": {
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
                "total_gst": total_gst
            }
        }), 200
        
    except Exception as error:
        conn.rollback()

        return jsonify({
            "message": (
                "Error fetching analytics data"
            ),
            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()