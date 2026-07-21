from flask import Flask
from flask_cors import CORS

from routes.customer_routes import customer_bp,customer
from routes.user_routes import user_bp,user
from routes.product_routes import product_bp,product
from routes.company_routes import company_bp,company
from routes.profile_routes import profile_bp
from routes.pi_routes import pi_bp,pi
from routes.ti_routes import ti_bp,ti
from routes.dashboard_routes import dashboard_bp
from routes.activity_routes import activity_bp,create_activity_table
from routes.analytics_routes import analytics_bp
from routes.utils_routes import utils_bp
from routes.pdf_routes import pdf_bp



# from database import db_connection
app = Flask(__name__)
CORS(app,origins="*")

app.register_blueprint(customer_bp)
app.register_blueprint(user_bp)
app.register_blueprint(product_bp)
app.register_blueprint(company_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(pi_bp)
app.register_blueprint(ti_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(utils_bp)
app.register_blueprint(pdf_bp)

if __name__ == "__main__":
    # db_connection()
    customer()
    user()
    product()
    company()
    pi()
    ti()
    create_activity_table()
    
    app.run(debug=True,host="0.0.0.0")