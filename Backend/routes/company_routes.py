
from flask import Blueprint, request, jsonify
from database_postgres import pg_connection

company_bp = Blueprint("company_bp", __name__)

# CREATE COMPANY TABLE
def company():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS company(
            company_id SERIAL PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL,
            gst_number VARCHAR(50) NOT NULL,
            pan_number VARCHAR(50),
            cin VARCHAR(100),

            street_address TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(100),
            pin_code VARCHAR(20),

            bank_name VARCHAR(255),
            account_number VARCHAR(100),
            account_type VARCHAR(100),

            cusd_id VARCHAR(100),
            ifsc_code VARCHAR(50),
            swift_code VARCHAR(50),

            branch_address TEXT,
            terms TEXT,
            payment_terms TEXT,
            pi_template VARCHAR(100),
            pi_start_no INTEGER DEFAULT 1,
            ti_template VARCHAR(100),
            ti_start_no INTEGER DEFAULT 1
                    )
    """)

    conn.commit()
    cur.close()
    conn.close()


# CREATE COMPANY
@company_bp.route("/company", methods=["POST"])
def add_company():
    
  

    data = request.get_json()
    
    pi_template = data.get("pi_template")
    pi_start_no = data.get("pi_start_no", 1)
    ti_template = data.get("ti_template")
    ti_start_no = data.get("ti_start_no", 1)

    

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO company(
            company_name,
            gst_number,
            pan_number,
            cin,
            street_address,
            city,
            state,
            country,
            pin_code,
            bank_name,
            account_number,
            account_type,
            cusd_id,
            ifsc_code,
            swift_code,
            branch_address,
            terms,
            payment_terms,
             pi_template,
            pi_start_no,
            ti_template,
            ti_start_no
        )
        VALUES(
            %s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s
        )
    """, (
        data["company_name"],
        data["gst_number"],
        data["pan_number"],
        data["cin"],
        data["street_address"],
        data["city"],
        data["state"],
        data["country"],
        data["pin_code"],
        data["bank_name"],
        data["account_number"],
        data["account_type"],
        data["cusd_id"],
        data["ifsc_code"],
        data["swift_code"],
        data["branch_address"],
        data["terms"],
        data["payment_terms"],
        pi_template,
        pi_start_no,
        ti_template,
        ti_start_no
    ))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "message": "Company Added Successfully"
    })


# GET ALL COMPANIES
@company_bp.route("/company", methods=["GET"])
def get_companies():

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM company
        ORDER BY company_id DESC
    """)

    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append({
            "company_id": row[0],
            "company_name": row[1],
            "gst_number": row[2],
            "pan_number": row[3],
            "cin": row[4],
            "street_address": row[5],
            "city": row[6],
            "state": row[7],
            "country": row[8],
            "pin_code": row[9],
            
            "bank_name": row[10],
            "account_number": row[11],
            "account_type": row[12],
            "cusd_id": row[13],
            "ifsc_code": row[14],
            "swift_code": row[15],
            "branch_address": row[16],
            
            "terms": row[17],
            "payment_terms": row[18],
            
            "pi_template": row[19],
            "pi_start_no": row[20],
            "ti_template": row[21],
            "ti_start_no": row[22]
            
            
        })

    cur.close()
    conn.close()

    return jsonify(result)


# GET SINGLE COMPANY
@company_bp.route("/company/<int:company_id>", methods=["GET"])
def get_company(company_id):
    
    

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM company
        WHERE company_id=%s
    """, (company_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return jsonify({
            "message": "Company Not Found"
        }), 404

    return jsonify({
        "company_id": row[0],
        "company_name": row[1],
        "gst_number": row[2],
        "pan_number": row[3],
        "cin": row[4],
        "street_address": row[5],
        "city": row[6],
        "state": row[7],
        "country": row[8],
        "pin_code": row[9],
        "bank_name": row[10],
        "account_number": row[11],
        "account_type": row[12],
        "cusd_id": row[13],
        "ifsc_code": row[14],
        "swift_code": row[15],
        "branch_address": row[16],
        "terms": row[17],
        "payment_terms": row[18],
        "pi_template": row[19],
        "pi_start_no": row[20],
        "ti_template": row[21],
        "ti_start_no": row[22]
    })


# UPDATE COMPANY
@company_bp.route("/company/<int:company_id>", methods=["PUT"])
def update_company(company_id):
    
    
    data = request.get_json()
    pi_template = data.get("pi_template")
    pi_start_no = data.get("pi_start_no", 1)
    ti_template = data.get("ti_template")
    ti_start_no = data.get("ti_start_no", 1)


    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE company
        SET
            company_name=%s,
            gst_number=%s,
            pan_number=%s,
            cin=%s,
            street_address=%s,
            city=%s,
            state=%s,
            country=%s,
            pin_code=%s,
            bank_name=%s,
            account_number=%s,
            account_type=%s,
            cusd_id=%s,
            ifsc_code=%s,
            swift_code=%s,
            branch_address=%s,
            terms=%s,
            payment_terms=%s,
             pi_template=%s,
        pi_start_no=%s,
        ti_template=%s,
        ti_start_no=%s
        WHERE company_id=%s
    """, (
        data["company_name"],
        data["gst_number"],
        data["pan_number"],
        data["cin"],
        data["street_address"],
        data["city"],
        data["state"],
        data["country"],
        data["pin_code"],
        data["bank_name"],
        data["account_number"],
        data["account_type"],
        data["cusd_id"],
        data["ifsc_code"],
        data["swift_code"],
        data["branch_address"],
        data["terms"],
        data["payment_terms"],
        pi_template,
        pi_start_no,
        ti_template,
        ti_start_no,

        company_id
    ))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "message": "Company Updated Successfully"
    })


# DELETE COMPANY
@company_bp.route("/company/<int:company_id>", methods=["DELETE"])
def delete_company(company_id):

    conn = pg_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM company
        WHERE company_id=%s
    """, (company_id,))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "message": "Company Deleted Successfully"
    })