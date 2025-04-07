import json
from flask import Flask, request
import db
from db import Account, Vendor, Lender, Equipment
from dotenv import load_dotenv
from sqlalchemy import create_engine
import os
from supabase import create_client, Client

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
PROJECTURL = os.getenv("projecturl")
ANONKEY = os.getenv("anonkey")

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
DIRECT_URL = f"postgresql://postgres.iwpicngrwgseirrrjhmj:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# Configure database URI
# ** Supabase Sample data URL**
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy with the Flask app
db.init_db(app)

DB = db.DatabaseDriver()

supabase: Client = create_client(PROJECTURL, ANONKEY)

#next two methods copy data over from supabase
def copy_account():
    """Copies Account table from supabase
    """
    response = supabase.table("Account").select('*').execute()
    data = response.data 
    with app.app_context():
        for item in data:
            row = Account(ID = item['ID'], Name = item['Name'], Street = item['Street'], 
                          City = item['City'], State = item['State'], ZIP = item['ZIP'], LiabilityEmail = item['LiabilityEmail'], 
                          PropertyEmail = item['PropertyEmail'], LiabilityExpirationDate = item['LiabilityExpirationDate'], 
                          PropertyExpirationDate = item['PropertyExpirationDate'], InsuranceCoordinator = item['InsuranceCoordinator'], 
                          InsuranceFolderID = item['InsuranceFolderID'])
            DB.session.add(row)
        DB.session.commit()

def copy_vendor():
    """Copies Vendor table from Supabase
    """
    response = supabase.table("Vendor").select('*').execute()
    data = response.data 
    with app.app_context():
        for item in data:
            row = Vendor(ID = item['ID'], Name = item['Name'], Street = item['Street'], 
                          City = item['City'], 
                          State = ['State'], ZIP = item['ZIP'], Webste = item['Website'], 
                          DnbHeadquartersState = item['DnbHeadquartersState'], DateScanned = item['DateScanned'], 
                          Flags = item['Flags'])
            DB.session.add(row)
        DB.session.commit()   


def success_response(body, code):
    return json.dumps(body), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code


#Endpoints from this point forward

@app.route("/account/")
def get_accounts():
    accounts = DB.get_accounts()
    return success_response({"accounts": accounts}, 200)


@app.route("/account/<string:account_id>/", methods=["GET"])
def get_account(account_id):
    account = DB.get_account_by_id(account_id)
    if account is None:
        return failure_response("Account not found")
    account["Equipment"] = DB.get_equipment_by_account_id(account_id)
    return success_response(account, 200)


@app.route("/vendorflags/<string:vendor_id>/", methods=["PATCH"])
def update_flags(vendor_id):
    """Include json with flag name {"flag": ___ }"""
    try:
        body = json.loads(request.data)
    except json.JSONDecodeError:
        return failure_response("Invalid JSON", 400)

    if "flag" not in body:
        return failure_response("Missing 'flag' in request body", 400)
    flag = body.get("flag")
    res = DB.update_flags(vendor_id, flag)
    if not res:
        return failure_response("Vendor does not exist")
    return success_response("Flags updated successfully", 204)


@app.route("/vendorflags/<string:vendor_id>/", methods=["GET"])
def get_flags(vendor_id):
    """Returns number of flags and names of flags that were added"""
    res = DB.get_vendor_by_id(vendor_id)

    if res is None:
        return failure_response("Vendor does not exist")
    return success_response({"Vendor.Flags":res.get("Vendor.Flags"), "Vendor.FlagsAdded": res.get("Vendor.FlagsAdded")}, 200)


@app.route("/vendor/")
def get_vendors():
    vendors = DB.get_vendors()
    return success_response({"vendors": vendors}, 200)


@app.route("/vendor/<string:vendor_id>/", methods=["GET"])
def get_vendor(vendor_id):
    """Returns all vendor information"""
    vendor = DB.get_vendor_by_id(vendor_id)
    if vendor is None:
        return failure_response("Vendor does not exist")
    return success_response(vendor, 200)


@app.route("/duediligence/", methods=["POST"])
def due_diligence():
    """Returns all information for due diligence check"""
    try:
        body = json.loads(request.data)
    except json.JSONDecodeError:
        return failure_response("Invalid JSON", 400)

    if "account_id" not in body:
        return failure_response("Missing 'account_id' in request body", 400)
    if "vendor_id" not in body:
        return failure_response("Missing 'vendor_id' in request body", 400)
    account_id = body["account_id"]
    vendor_id = body["vendor_id"]
    res = DB.due_diligence_check(account_id, vendor_id)
    if not res:
        failure_response("Something went wrong", 404)
    return success_response(res, 200)


@app.route("/secofstate/<string:state_name>/", methods=["GET"])
def secretary_of_state_link(state_name):
    """
    Task 2: Enter state name with no spaces. Returns corresponding secretary of state links.
    """
    with app.app_context():
        res = DB.get_state_link(state_name.lower())
        if res is None:
            return failure_response("State not found")
        return success_response({"state": state_name, "url": res}, 200)


def main():
    app.run(host="0.0.0.0", port=8000, debug=True)
    copy_account()
    copy_vendor()


if __name__ == "__main__":
    main()