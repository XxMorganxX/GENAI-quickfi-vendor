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

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
PERPLEXITY_API_KEY = os.getenv("perplexity_api_key")


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
    """
    Compares vendor and account names/addresses for matches and updates flags accordingly.
    """
    try:
        # Use database driver to get due diligence data
        data = db_driver.due_diligence_check(account_id, vendor_id)
        if data is None:
            print("Failed to get due diligence data")
            return None
            
        matches_found = False
        
        vendor_name = data["Vendor.Name"]
        vendor_address = data["Vendor.Address"]
        account_name = data["Account.Name"]
        account_address = data["Account.Address"]
        
        # Check for matches and update flags
        if vendor_name == account_name or vendor_address == account_address:
            matches_found = True
            
            # Update vendor flags directly through database driver
            flag_type = "name/address"
            update_success = db_driver.update_flags(vendor_id, flag_type)
            
            if not update_success:
                print(f"Failed to update flags for vendor {vendor_id}")
        
        return {
            "matches_found": matches_found,
            "data": data
        }
    
    except Exception as e:
        print(f"Operation failed: {str(e)}")
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
        








# Task 3 Docs:
# **What AI does**:

# - Looks up the vendor in their state's official business registry using the `DNBaddress.state`

# **Where it connects to**:

# - Public Secretary of State websites (listed in SOS lookup table)
#     - e.g., for California: https://bizfileonline.sos.ca.gov/search/business

# **Steps**:

# 1. Use `GET /states/secretary-of-state-urls` to get the right URL
# 2. Search vendor by name
# 3. Scrape or read results

# **What AI checks**:

# - **Years in Business**:
#     - If < 5 years → flag
# - **Business Status**:
#     - If status ≠ "Active" → flag
# - **If vendor is not found at all** → flag

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

def google_search_validation(vendor_name, vendor_address):
    """
    Uses Perplexity to Google search for the vendor and extracts the top Google
    Business result.
    Raises flags if any of the following:
    - No business found
    - No business website found
    - No address listed on the business
    - Address listed on Google or business site does not match vendor address

    Args:
        vendor_name (str): The name of the vendor
        vendor_address (str): The address of the vendor

    Returns:
        flags (list of str): Flags indicating issues with the vendor
    """
    # Create a prompt for Perplexity to Google search for the vendor and extract business address and website data
    prompt = f"""
        Please search for the business '{vendor_name}' on Google.

        1. Is a Google Business listing with an address found?
        2. Does this address match the address '{vendor_address}'?
        3. Does the business have a website listed?
        4. Is the site accessible with an address listed on the homepage or contact page, and
            does this address match the address '{vendor_address}'?

        Respond in JSON in the following format:
        {{
            "google_business_found": true/false,
            "google_address_match": true/false,
            "website_found": true/false,
            "website_address_found": true/false,
            "website_address_match": true/false
        }}
        """
    try:
        # Input this prompt to Perpexity and parse the response
        perplexity_response = call_perplexity_api(prompt)
        response = json.loads(perplexity_response)

        # Flag for no business found, no website found, no address listed, or mismatched addresses
        flags = []
        if not response["google_business_found"]:
            flags.append("No Google business listing found")
        else:
            if not response["google_address_match"]:
                flags.append("Google Business address does not match vendor address")
            if not response["website_found"]:
                flags.append("No business website could be found")
            elif not response["website_address_found"] or not response["website_address_match"]:
                flags.append("Address listed on website does not match vendor address")
        return flags
    except Exception as e:
        raise RuntimeError(f"Failed to Google search for vendor {vendor_name}.")

def google_maps_validation(vendor_address):
    """
    Uses Google Maps API to validate whether the vendor address corresponds to a
    physical location that is likely to be a business.

    Args:
        vendor_address (str): The vendor address to check

    Returns:
        list of str: Flags indicating issues with the address
    """
    # Geocode the address
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": vendor_address,
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        geo_response = requests.get(geocode_url, params=params).json()

        if geo_response["status"] != "OK" or len(geo_response["results"]) == 0:
            return ["Address details could not be found."]

        result = geo_response["results"][0]
        location_type = result["geometry"]["location_type"]
        place_id = result.get("place_id")

        # If the location is not a physical building, flag
        if location_type != "ROOFTOP":
            return ["Address does not appear to a business establishment."]

        if place_id:
            places_url = "https://maps.googleapis.com/maps/api/place/details/json"
            place_params = {
                "place_id": place_id,
                "key": GOOGLE_MAPS_API_KEY,
                "fields": "name,business_status,types"
            }

            place_response = requests.get(places_url, params=place_params).json()

            if place_response.get("status") == "OK":
                types = place_response["result"].get("types", [])
                # If the location type does not correspond to a business, flag
                if "establishment" not in types and "point_of_interest" not in types:
                    return ["Address does not appear to a business establishment."]
                # If the location type corresponds to a PO box, flag
                if "post_office" in types or "mailbox" in types:
                    return ["Address does not appear to a business establishment."]
            else:
                return ["Address details could not be found."]
        else:
            return ["Address details could not be found."]

    except Exception as e:
        return ["Address details could not be found."]

    return []

def task_five(vendor_id):
    """
    Performs validation of vendors using Perplexity for Google search and Google
    Maps API for Google Maps search.
    Raises flags if Google Business profile cannot be found, mismatched address
    on Google or website, no business website found or no address listed, or
    address does not appear to be a physical building (e.g. vacant lot, P.O. box).

    Args:
        vendor_id (str): The vendor id

    Returns:
        dict:
            {
                "flags": List of flag messages that were raised
                "num_flags": Integer count of flags raised
            }
    """
    # Get vendor name and address
    vendor_info = db_driver.get_vendor_by_id(vendor_id)
    if not vendor_info:
        raise ValueError(f"Vendor ID '{vendor_id}' not found")
    vendor_name = vendor_info["Vendor.Name"]
    vendor_address = vendor_info["Vendor.Address"]

    # Raise business address and website flags
    address_website_flags = google_search_validation(vendor_name, vendor_address)
    num_flags = len(address_website_flags)

    # Raise Google Maps presence flag
    maps_flags = google_maps_validation(vendor_address)
    num_flags += len(maps_flags)

    # Increment flags
    result = requests.patch(f"{API_BASE_URL}/vendorflags/{vendor_id}/", json={"num_flags": num_flags})
    if result.status_code != 204:
        print(f"Failed to update flags for vendor id {vendor_id}: {result.status_code}")

    return {
        "flags": address_website_flags + maps_flags,
        "num_flags": num_flags
    }

def task_six(vendor_id):
    """
    Use Perplexity to search for adverse news associated with a vendor.
    Performs a Google search using the vendor's name and flag if any results
    suggest legal trouble, bankruptcy, fraud, or negative media.

    Args:
        vendor_id (str): Identifier of the vendor

    Returns:
        dict:
            {
                "flags": List of flag messages that were raised
                "num_flags": Integer count of flags raised
            }
    """
    # Get vendor name
    vendor_info = db_driver.get_vendor_by_id(vendor_id)
    if not vendor_info:
        raise ValueError(f"Vendor ID '{vendor_id}' not found")
    vendor_name = vendor_info["Vendor.Name"]

    # Create a prompt to search for adverse news associated with the vendor
    keywords = ["fraud", "lawsuit", "shutdown", "bankruptcy", "charges", "scam", "indictment", "settlement", "scandal"]
    prompt = f"""
        Google search for news about '{vendor_name}' combined with any of the following terms: {', '.join(keywords)}.

        Check the top 5 results of each search.

        Check if any of the results mention the vendor being involved in:
        - Fraud
        - Lawsuits or legal disputes
        - Bankruptcy or shutdown
        - Government charges or fines
        - Negative media exposure or public scandal

        Return a JSON object in the following format:
        {{
          "adverse_findings": true/false,
          "flag_reasons": ["List of short descriptions of adverse finding such as 'Bankruptcy filing in 2020' or 'Lawsuit from partner'"]
        }}
    """
    try:
        # Call Perplexity on the prompt
        perplexity_response = call_perplexity_api(prompt)
        response = json.loads(perplexity_response)

        # Raise flags
        if not response["adverse_findings"]:
            return {"flags": [], "num_flags": 0}
        num_flags = len(response["flag_reasons"])
        result = requests.patch(f"{API_BASE_URL}/vendorflags/{vendor_id}/", json={"num_flags": num_flags})
        if result.status_code != 204:
            print(f"Failed to update flags for vendor id {vendor_id}: {result.status_code}")

        return {
            "flags": response["flag_reasons"],
            "num_flags": num_flags
        }
    except Exception as e:
        raise RuntimeError(f"Failed to run adverse news search for vendor {vendor_name}.")

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
        

        body = f"- Vendor Name: {vendor_name}\n - Vendor Address: {vendor_address}\n\n - Summary of Flags:\n{flag_summary}"
        send_email(body, vendor_name)
