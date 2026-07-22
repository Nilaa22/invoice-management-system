from flask import Blueprint, jsonify
from database_postgres import pg_connection
from psycopg2.extras import RealDictCursor

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/admin-dashboard", methods=["GET"])
def get_admin_dashboard():
    conn = pg_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT COUNT(*) AS total_pi
            FROM pi_bills
        """)
        total_pi = cur.fetchone()["total_pi"]

        cur.execute("""
            SELECT COUNT(*) AS total_ti
            FROM ti_bills
        """)
        total_ti = cur.fetchone()["total_ti"]

        cur.execute("""
            SELECT COUNT(*) AS total_products
            FROM products
        """)
        total_products = cur.fetchone()["total_products"]

        cur.execute("""
            SELECT COUNT(*) AS total_customers
            FROM customers
        """)
        total_customers = cur.fetchone()["total_customers"]

        cur.execute("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_sales
            FROM ti_bills
        """)
        total_sales = cur.fetchone()["total_sales"]

        cur.execute("""
            SELECT COALESCE(
                SUM(COALESCE(balance_amount, total_amount)),
                0
            ) AS total_pending
            FROM ti_bills
        """)
        total_pending = cur.fetchone()["total_pending"]

        cur.execute("""
            SELECT COUNT(*) AS paid_invoices
            FROM ti_bills
            WHERE LOWER(COALESCE(status, 'unpaid')) = 'paid'
        """)
        paid_invoices = cur.fetchone()["paid_invoices"]

        cur.execute("""
            SELECT COUNT(*) AS partial_invoices
            FROM ti_bills
            WHERE LOWER(COALESCE(status, 'unpaid')) = 'partial'
        """)
        partial_invoices = cur.fetchone()["partial_invoices"]

        cur.execute("""
            SELECT COUNT(*) AS unpaid_invoices
            FROM ti_bills
            WHERE LOWER(COALESCE(status, 'unpaid')) = 'unpaid'
        """)
        unpaid_invoices = cur.fetchone()["unpaid_invoices"]

        cur.execute("""
            SELECT
                activity_id,
                activity_type,
                action,
                title,
                description,
                reference_id,
                reference_number,
                user_id,
                user_name,
                created_at
            FROM activity_logs
            ORDER BY created_at DESC, activity_id DESC
           
        """)

        activity_rows = cur.fetchall()

        activities = []

        for activity in activity_rows:
            activities.append({
                "activity_id": activity["activity_id"],
                "type": activity["activity_type"],
                "action": activity["action"],
                "title": activity["title"],
                "desc": activity["description"],
                "reference_id": activity["reference_id"],
                "reference_number": activity["reference_number"],
                "user_id": activity["user_id"],
                "user_name": activity["user_name"],
                "time": (
                    activity["created_at"].strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                    if activity["created_at"]
                    else ""
                )
            })

        return jsonify({
            "total_sales": float(total_sales or 0),
            "total_pending": float(total_pending or 0),

            "total_pi": int(total_pi or 0),
            "total_products": int(total_products or 0),
            "total_customers": int(total_customers or 0),

            "total_ti": int(total_ti or 0),
            "paid_invoices": int(paid_invoices or 0),
            "partial_invoices": int(partial_invoices or 0),
            "unpaid_invoices": int(unpaid_invoices or 0),

            "activities": activities
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Error fetching dashboard data",
            "error": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()
        


@dashboard_bp.route(
    "/user-dashboard/<int:user_id>",
    methods=["GET"]
)
def get_user_dashboard(user_id):
    conn = pg_connection()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        # ----------------------------------
        # Customers created by this user
        # ----------------------------------

        cur.execute("""
            SELECT COUNT(DISTINCT reference_id)
                AS total
            FROM activity_logs
            WHERE user_id = %s
              AND activity_type = 'customer'
              AND action = 'created'
        """, (user_id,))

        customer_result = cur.fetchone()

        total_customers = int(
            customer_result["total"] or 0
        )

        # ----------------------------------
        # Products created by this user
        # ----------------------------------

        cur.execute("""
            SELECT COUNT(DISTINCT reference_id)
                AS total
            FROM activity_logs
            WHERE user_id = %s
              AND activity_type = 'product'
              AND action = 'created'
        """, (user_id,))

        product_result = cur.fetchone()

        total_products = int(
            product_result["total"] or 0
        )

        # ----------------------------------
        # PI created by this user
        # ----------------------------------

        cur.execute("""
            SELECT COUNT(DISTINCT reference_id)
                AS total
            FROM activity_logs
            WHERE user_id = %s
              AND activity_type = 'pi'
              AND action = 'created'
        """, (user_id,))

        pi_result = cur.fetchone()

        total_pi = int(
            pi_result["total"] or 0
        )

        # ----------------------------------
        # TI created by this user
        # ----------------------------------

        cur.execute("""
            SELECT COUNT(DISTINCT reference_id)
                AS total
            FROM activity_logs
            WHERE user_id = %s
              AND activity_type = 'ti'
              AND action = 'created'
        """, (user_id,))

        ti_result = cur.fetchone()

        total_ti = int(
            ti_result["total"] or 0
        )

        # ----------------------------------
        # Recent activities by this user
        # ----------------------------------

        cur.execute("""
            SELECT
                activity_id,
                activity_type,
                action,
                title,
                description,
                reference_id,
                reference_number,
                user_id,
                user_name,
                created_at
            FROM activity_logs
            WHERE user_id = %s
            ORDER BY
                created_at DESC,
                activity_id DESC
        
        """, (user_id,))

        activity_rows = cur.fetchall()

        activities = []

        for activity in activity_rows:
            activities.append({
                "activity_id":
                    activity["activity_id"],

                "type":
                    activity["activity_type"],

                "action":
                    activity["action"],

                "title":
                    activity["title"],

                "desc":
                    activity["description"],

                "reference_id":
                    activity["reference_id"],

                "reference_number":
                    activity["reference_number"],

                "user_id":
                    activity["user_id"],

                "user_name":
                    activity["user_name"],

                "time": (
                    activity["created_at"].strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                    if activity["created_at"]
                    else ""
                )
            })

        return jsonify({
            "customers": total_customers,
            "products": total_products,
            "pi": total_pi,
            "ti": total_ti,
            "activities": activities
        }), 200

    except Exception as error:
        conn.rollback()

        return jsonify({
            "message":
                "Error fetching user dashboard data",

            "error": str(error)
        }), 500

    finally:
        cur.close()
        conn.close()