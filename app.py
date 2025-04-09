import json
from flask import Flask, request, jsonify
import db
# from db import Account, Vendor, Lender, Equipment
from dotenv import load_dotenv
import os
from supabase import create_client, Client

# Load environment variables from .env
load_dotenv()

# Create the Flask application
app = Flask(__name__)

# Fetch Supabase variables
PROJECTURL = os.getenv("projecturl")
ANONKEY = os.getenv("anonkey")

DB = db.DatabaseDriver()

def success_response(body, code):
    return json.dumps(body), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code

@app.route("/account/")
def get_accounts():
    """Returns all accounts (sample data)"""
    accounts = DB.get_accounts()
    return success_response({"accounts": accounts}, 200)

@app.route("/vendor/")
def get_vendors():
    """Returns all vendors (sample data)"""
    vendors = DB.get_vendors()
    return success_response({"vendors": vendors}, 200)
 

@app.route("/account/<string:account_id>/", methods=["GET"])
def get_account(account_id):
    """
    Fetches account information by account ID using the get_account_by_id method in db.py.
    """
    account = DB.get_account_by_id(account_id)  
    if account is None:
        return failure_response("Account not found", 404)  
    return success_response(account, 200) 


@app.route("/vendorflags/<string:vendor_id>/", methods=["PATCH"])
def update_flags(vendor_id):
    """Adds a flag to a vendor. Input the flag name.
    """
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
    res = DB.get_flags(vendor_id)

    if res is None:
        return failure_response("Vendor does not exist")
    return success_response(res, 200)


@app.route("/vendor/<string:vendor_id>/", methods=["GET"])
def get_vendor(vendor_id):
    """Returns the information for a vendor.
    """
    vendor = DB.get_vendor_by_id(vendor_id)
    if vendor is None:
        return failure_response("Vendor does not exist")
    return success_response(vendor, 200)


@app.route("/duediligence/", methods=["POST"])
def due_diligence():
    """Returns information needed to run due diligence check.
    """
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
    if res is None:
        failure_response("Something went wrong", 404)
    return success_response(res, 200)


@app.route("/secofstate/<string:state_name>/", methods=["GET"])
def secretary_of_state_link(state_name):
    """
    Task 2: Enter state name with no spaces. Returns corresponding secretary of state links.
    """
    res = DB.get_state_link(state_name.lower())
    if res is None:
        return failure_response("State not found")
    return success_response({"state": state_name, "url": res}, 200)


@app.route("/vendor/<string:vendor_id>/sos/", methods=["PATCH"])
def update_sos(vendor_id):
    """Updates Secretary of State information for a vendor.
    Expected JSON body: {"years": float, "active": boolean}
    """
    try:
        body = json.loads(request.data)
    except json.JSONDecodeError:
        return failure_response("Invalid JSON", 400)

    if "years" not in body or "active" not in body:
        return failure_response("Missing 'years' or 'active' in request body", 400)

    years = body["years"]
    active = body["active"]

    res = DB.update_sos_info(vendor_id, years, active)
    if not res:
        return failure_response("Vendor does not exist")
    return success_response("SOS info updated successfully", 200)


@app.route("/vendor/<string:vendor_id>/ofac/", methods=["PATCH"])
def update_ofac(vendor_id):
    """Updates OFAC information for a vendor.
    Expected JSON body: {"hit_found": boolean}
    """
    try:
        body = json.loads(request.data)
    except json.JSONDecodeError:
        return failure_response("Invalid JSON", 400)

    if "hit_found" not in body:
        return failure_response("Missing 'hit_found' in request body", 400)

    hit_found = body["hit_found"]
    res = DB.update_ofac_info(vendor_id, hit_found)
    if not res:
        return failure_response("Vendor does not exist")
    return success_response("OFAC info updated successfully", 200)


def main():
    app.run(host="0.0.0.0", port=8000, debug=True)

if __name__ == "__main__":
    main()