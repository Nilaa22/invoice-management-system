
from flask import Blueprint, request, jsonify
from database_postgres import pg_connection
from routes.activity_routes import add_activity

product_bp = Blueprint("product_bp", __name__)

# CREATE TABLE PRODUCT
def product():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products(
            product_id SERIAL PRIMARY KEY,
            product_name VARCHAR(255) NOT NULL,
            product_discription TEXT,
            price NUMERIC(10,2) NOT NULL,
            hsn_sac_code VARCHAR(50),
            tax_type VARCHAR(50) NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


# CREATE PRODUCT
@product_bp.route("/product", methods=["POST"])
def add_product():

    data = request.get_json()
   

    actor_user_id = data.get("actor_user_id")
    actor_user_name = data.get("actor_user_name")

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products(
            product_name,
            product_discription,
            price,
            hsn_sac_code,
            tax_type
        )
        VALUES (%s,%s,%s,%s,%s)
        RETURNING product_id
    """, (
        data.get("product_name"),
        data.get("product_discription"),
        data.get("price"),
        data.get("hsn_sac_code"),
        data.get("tax_type")
    ))
    product_id = cur.fetchone()[0]
    add_activity(
    activity_type="product",
    action="created",
    title="New product added",
    description=f'Product "{data.get("product_name")}" has been added',
    reference_id=product_id,
    user_id=actor_user_id,
    user_name=actor_user_name,
    conn=conn
)

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "message": "Product Added Successfully"
    })


# GET ALL PRODUCTS
@product_bp.route("/product", methods=["GET"])
def get_products():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM products
        ORDER BY product_id ASC
    """)

    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append({
            "product_id": row[0],
            "product_name": row[1],
            "product_discription": row[2],
            "price": float(row[3]),
            "hsn_sac_code": row[4],
            "tax_type": row[5]
        })

    cur.close()
    conn.close()

    return jsonify(result)



# GET SINGLE PRODUCT
@product_bp.route("/product/<int:product_id>", methods=["GET"])
def get_product(product_id):

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM products
        WHERE product_id=%s
    """, (product_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return jsonify({
            "message": "Product Not Found"
        }), 404

    return jsonify({
        "product_id": row[0],
        "product_name": row[1],
        "product_discription": row[2],
        "price": float(row[3]),
        "hsn_sac_code": row[4],
        "tax_type": row[5]
    })


# UPDATE PRODUCT
@product_bp.route("/product/<int:product_id>", methods=["PUT"])
def update_product(product_id):

    data = request.get_json()
    actor_user_id = data.get("actor_user_id")
    actor_user_name = data.get("actor_user_name")

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE products
        SET
            product_name=%s,
            product_discription=%s,
            price=%s,
            hsn_sac_code=%s,
            tax_type=%s
        WHERE product_id=%s
    """, (
        data["product_name"],
        data["product_discription"],
        data["price"],
        data["hsn_sac_code"],
        data["tax_type"],
        product_id
    ))
    add_activity(
    activity_type="product",
    action="updated",
    title="Product updated",
    description=f'Product "{data.get("product_name")}" has been updated',
    reference_id=product_id,
    user_id=actor_user_id,
    user_name=actor_user_name,
    conn=conn
)

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "message": "Product Updated Successfully"
    })

# DELETE THE PRODUCT
@product_bp.route("/product/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):

    conn = pg_connection()
    cur = conn.cursor()

    try:
        data = request.get_json() or {}

        actor_user_id = data.get("actor_user_id")
        actor_user_name = data.get("actor_user_name")

        # Get product details
        cur.execute("""
            SELECT product_name
            FROM products
            WHERE product_id = %s
        """, (product_id,))

        product = cur.fetchone()

        if not product:
            return jsonify({"message": "Product not found"}), 404

        product_name = product[0]

        # Log activity
        add_activity(
            activity_type="product",
            action="deleted",
            title="Product Deleted",
            description=f'Product "{product_name}" has been deleted',
            reference_id=product_id,
            user_id=actor_user_id,
            user_name=actor_user_name,
            conn=conn
        )

        # Delete product
        cur.execute("""
            DELETE FROM products
            WHERE product_id = %s
        """, (product_id,))

        conn.commit()

        return jsonify({
            "message": "Product Deleted Successfully"
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "message": "Error deleting product",
            "error": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()