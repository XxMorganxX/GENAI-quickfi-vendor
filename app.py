import json
from flask import Flask, request
import db
from dotenv import load_dotenv
from sqlalchemy import create_engine
import os

# Load environment variables from .env
load_dotenv()

# Create the Flask application
app = Flask(__name__)

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)
# If using Transaction Pooler or Session Pooler, we want to ensure we disable SQLAlchemy client side pooling -
# https://docs.sqlalchemy.org/en/20/core/pooling.html#switching-pool-implementations
# engine = create_engine(DATABASE_URL, poolclass=NullPool)

# Test the connection
try:
    with engine.connect() as connection:
        print("Connection successful!")
except Exception as e:
    print(f"Failed to connect: {e}")


# Direct connection to the database. Used for migrations.
DIRECT_URL="postgresql://postgres.iwpicngrwgseirrrjhmj:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# Configure database URI
# ** Supabase Sample data URL**
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy with the Flask app
db.init_db(app)


DB = db.DatabaseDriver()


def success_response(body, code):
    return json.dumps(body), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code


@app.route("/account/<int:account_id>/", methods=["GET"])
def get_account(account_id):
    account = DB.get_account_by_id(account_id)
    if account is None:
        return failure_response("Account not found")
    account["Equipment"] = DB.get_equipment_by_account_id(account_id)
    return success_response(account, 200)


@app.route("/vendor/<int:vendor_id>/", methods=["PATCH"])
def update_flags(vendor_id, num_flags):
    res = DB.update_flags(vendor_id, num_flags)
    if not res:
        failure_response("Vendor does not exist")
    return success_response("Flags updated successfully", 204)


"""
Task 2: Enter state name with no spaces. Returns corresponding secretary of state links. 
"""
  
@app.route("/secofstate/<string:state_name>/", methods=["GET"])
def secretary_of_state_link(state_name):
    with app.app_context():
        res = DB.get_state_link(state_name.lower())
        if res is None:
            return failure_response("State not found")
        return success_response({"link":res}, 200)

def main():
    app.run(host="0.0.0.0", port=8000, debug=True)


if __name__ == "__main__":
    main()
