import json
from flask import Flask, request
import db

DB = db.DatabaseDriver()

app = Flask(__name__)


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


@app.route("/upload", methods=["POST"])
def upload_pdf():
    pass


@app.route("/account/<int:account_id>/", methods=["PATCH"])
def update_account(account_id):
    pass

def main():
    app.run(host="0.0.0.0", port=8000, debug=True)


if __name__ == "__main__":
    main()
