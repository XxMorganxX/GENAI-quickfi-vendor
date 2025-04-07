# Database
from db import DatabaseDriver
import requests
db_driver = DatabaseDriver()

# Emailing
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Environment variables
import os
from dotenv import load_dotenv
load_dotenv()



"""
Morgan Questions:

- is this the proper route to the database?
- rename the functions to be more descriptive
- for task 1, should each comparison be a single flag or a flag per comparison?

"""



# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")


# CONSTANTS
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"



"""
TASK ONE DOCS:

- Compares `Vendor.Name` with `Account.Name`
- Compares `Vendor.Address` with `Account.Address`
- To detect if the vendor and borrower are the same entity (which is a red flag)

**Logic**:

- If `Vendor.Name === Account.Name` → flag
- If `Vendor.Address === Account.Address` → flag
"""
def task_one(account_id, vendor_id):
    try:
        payload = {
                "account_id": account_id,
                "vendor_id": vendor_id
        }
        
        request_endpoint = f"{DATABASE_URL}/duediligence/"
    
        # Make the POST request
        response = requests.post(request_endpoint, json=payload)
        
        if response.status_code == 200:
                return response.json()
        
        data = response.json()
                
        vendor_name, vendor_address = data["Vendor.Name"], data["Vendor.Address"]
        account_name, account_address = data["Account.Name"], data["Account.Address"]
        
        if vendor_name == account_name or vendor_address == account_address:
            matches_found = True
            
            # Update vendor via PATCH endpoint
            patch_endpoint = f"{DATABASE_URL}/vendor/{vendor_id}/"
            patch_payload = {  # Increment flag count
                "match_type": "name" if vendor_name == account_name else "address"
            }
            
            patch_response = requests.patch(patch_endpoint, json=patch_payload)
            
            if patch_response.status_code != 200:
                print(f"Failed to update vendor. Status code: {patch_response.status_code}")
                print(f"Response: {patch_response.text}")
        
        return {
            "matches_found": matches_found,
            "data": data
        }
                
        
    
    except Exception as e:
        print(f"Database operation failed: {str(e)}")
        raise



"""
TASK TWO DOCS:

- Uses `Vendor.Name` + `Vendor.Address` to search the DNB API 
- Connects to the DNB API (paid/commercial access) or public search: [https://www.dnb.com](https://www.dnb.com/)

**What AI looks for**:

- **Prescreen Score**:
    - If "High Risk" → flag
- **Headquarters Address**:
    - Save this address as `DNBaddress` to determine which state’s Secretary of State website to use in the next step

**Data Used Later**:

- `DNBaddress.state` → to find correct Secretary of State lookup URL

"""
def task_two(vendor_id):
        


def send_email(body, vendor_name, recipient_email=None):
    """
    Send an email using SMTP.
    
    Args:
        subject (str): Subject line of the email
        body (str): Body content of the email
        recipient_email (str, optional): Email address of recipient. If None, uses EMAIL_RECIPIENT from env
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Email configuration
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        # Use default recipient if none provided
        if recipient_email is None:
            recipient_email = os.getenv("EMAIL_RECIPIENT")
            if not recipient_email:
                raise ValueError("No recipient email provided and EMAIL_RECIPIENT not set in environment")

        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = f"Vendor Due Diligence Flags - {vendor_name}"

        # Add body
        message.attach(MIMEText(body, "plain"))

        # Create SMTP session
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Enable TLS
            server.login(sender_email, sender_password)
            server.send_message(message)

        return True

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def task_seven_flag_report(vendor_name, vendor_address, flag_summary):
        flag_summary = "NOT IMPLEMENTED YET"
        
        body = f"- Vendor Name: {vendor_name}\n - Vendor Address: {vendor_address}\n\n - Summary of Flags:\n{flag_summary}"
        send_email(body, vendor_name)