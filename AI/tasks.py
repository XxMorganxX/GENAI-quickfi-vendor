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

import json
import csv
from pathlib import Path

import playwright



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
    - Save this address as `DNBaddress` to determine which state's Secretary of State website to use in the next step

**Data Used Later**:

- `DNBaddress.state` → to find correct Secretary of State lookup URL

"""
def task_two(vendor_id):
        pass







"""
Task 3 Docs:
**What AI does**:

- Looks up the vendor in their state's official business registry using the `DNBaddress.state`

**Where it connects to**:

- Public Secretary of State websites (listed in SOS lookup table)
    - e.g., for California: https://bizfileonline.sos.ca.gov/search/business

**Steps**:

1. Use `GET /states/secretary-of-state-urls` to get the right URL
2. Search vendor by name
3. Scrape or read results

**What AI checks**:

- **Years in Business**:
    - If < 5 years → flag
- **Business Status**:
    - If status ≠ "Active" → flag
- **If vendor is not found at all** → flag
"""
def call_perplexity_api(prompt):
    """
    Call the Perplexity API to analyze HTML content.
    
    Args:
        prompt (str): Prompt to send to Perplexity
        
    Returns:
        str: Perplexity's response
    """
    try:
        # This is a placeholder for your actual Perplexity API call
        # You would need to implement this based on Perplexity's API documentation
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "prompt": prompt,
            "model": "pplx-7b-online"  # Or whatever model is appropriate
        }
        
        response = requests.post(
            "https://api.perplexity.ai/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["completion"]
        else:
            return json.dumps({
                "found": False,
                "registration_date": None,
                "years_in_business": None,
                "status": None,
                "explanation": f"API error: {response.status_code}"
            })
            
    except Exception as e:
        return json.dumps({
            "found": False,
            "registration_date": None,
            "years_in_business": None,
            "status": None,
            "explanation": f"Error calling Perplexity API: {str(e)}"
        })
    
def get_sos_search_results(sos_url, vendor_name):
    """
    Navigate to a Secretary of State website and perform a search.

    Args:
        sos_url (str): URL of the Secretary of State website
        vendor_name (str): Name of the vendor to search for
        
    Returns:
        str: HTML content of the search results page
    """
    try:
        # Initialize browser (headless mode)
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to the SOS website
        page.goto(sos_url)
        
        # Take a simple approach - just find any input field and enter the vendor name
        # This won't work for all sites but gives Perplexity something to analyze
        input_selectors = [
            'input[type="text"]',
            'input[name*="name"]',
            'input[name*="search"]',
            'input[name*="entity"]',
            'input[id*="name"]',
            'input[id*="search"]',
            'input[id*="entity"]'
        ]
        
        for selector in input_selectors:
            if page.query_selector(selector):
                page.fill(selector, vendor_name)
                break
        
        # Look for a submit button and click it
        button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Search")',
            'button:has-text("Lookup")',
            'a:has-text("Search")'
        ]
        
        for selector in button_selectors:
            if page.query_selector(selector):
                page.click(selector)
                break
        
        # Wait for results to load
        page.wait_for_load_state("networkidle")
        
        # Get the HTML content
        html_content = page.content()
        
        # Clean up
        browser.close()
        
        return html_content
        
    except Exception as e:
        print(f"Error navigating to SOS website: {str(e)}")
        return f"<error>Failed to navigate to {sos_url}: {str(e)}</error>"
    
def get_state_sos_url(state):
    """
    Get the Secretary of State URL for a given state from the CSV file.
    
    Args:
        state (str): State name in lowercase (e.g., "california")
        
    Returns:
        str: URL for the state's Secretary of State website, or None if not found
    """
    try:
        # Get the path to the CSV file
        # Assuming the CSV is in the same directory as this script
        current_dir = Path(__file__).parent.parent
        csv_path = current_dir / "secretary_of_state_lookup.csv"
        
        # Read the CSV file
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Convert state to title case for comparison (e.g., "california" -> "California")
            state_title = state.title()
            
            # Search for the state in the CSV
            for row in reader:
                if row['state'] == state_title:
                    return row['url']
            
            # If state not found
            return None
            
    except Exception as e:
        print(f"Error reading Secretary of State URL for {state}: {str(e)}")
        return None

def check_secretary_of_state(vendor_name, state):
    """
    Use Perplexity AI to check a vendor's status in a Secretary of State database.
    
    Args:
        vendor_name (str): Name of the vendor to check
        state (str): State abbreviation (e.g., "CA" for California)
        
    Returns:
        dict: Results including found status, years in business, and active status
    """
    try:
        # Get the appropriate Secretary of State URL
        sos_url = get_state_sos_url(state.lower())
        if not sos_url:
            return {"error": f"No Secretary of State URL found for {state}"}
            
        # Use a web browser automation tool to navigate to the SOS website
        # and perform a basic search for the vendor name
        html_content = get_sos_search_results(sos_url, vendor_name)
        
        # Create a prompt for Perplexity
        prompt = f"""
        I need to check if the business "{vendor_name}" is registered in {state} and extract specific information.
        
        Based on the HTML content from the Secretary of State website, please tell me:
        
        1. Is the business found in the registry? (Yes/No)
        2. The age of the business (in number of years), based on the business's registration date (MM/DD/YYYY) to today?
        3. If the current status of the business is "Active" or something of equal meaning. Also have the status.
        
        Please return your answer in JSON format:
        {{
            "found": true/false,
            "years_in_business": number or null,
            "status": "status text" or null,
            "active": true/false,
            "explanation": "brief explanation of findings"
        }}
        
        HTML content:
        {html_content}
        """
        
        # Call Perplexity API
        perplexity_response = call_perplexity_api(prompt)
        
        # Parse the response (assuming Perplexity returns well-formed JSON)
        results = json.loads(perplexity_response)
        
        # Determine if any flags should be set based on the criteria
        flags = []
        if not results["found"]:
            flags.append("Business not found in registry")
        elif results["years_in_business"] is not None and results["years_in_business"] < 5:
            flags.append(f"Business operating for only {results['years_in_business']} years")
        elif results["status"] is not None and results["active"] == False:
            flags.append(f"Business status is '{results['status']}' instead of 'Active'")
            
        results["flags"] = flags
        results["flag_count"] = len(flags)
        
        return results
        
    except Exception as e:
        return {"error": str(e), "flags": ["Error checking Secretary of State"], "flag_count": 1}



def task_three():
     pass







def task_four():
     pass

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