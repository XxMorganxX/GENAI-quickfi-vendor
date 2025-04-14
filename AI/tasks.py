import sys, os
# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

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
from dotenv import load_dotenv
load_dotenv()

import json, csv, base64, time
from pathlib import Path

from playwright.async_api import async_playwright
import re



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

# Gets dnb api access token
def get_access_token():
	# Sandbox endpoint URL for token request
	url = "https://login.bisnode.com/sandbox/v1/token.oauth2"

	client_id = os.getenv("client_id")
	client_secret = os.getenv("client_secret")
	request_scope = "credit_data_companies"

	# Combine client credentials and encode them in Base64
	credentials = f"{client_id}:{client_secret}"
	encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

	# Set up headers including Content-Type and Authorization
	headers = {
		"Content-Type": "application/x-www-form-urlencoded",
		"Authorization": f"Basic {encoded_credentials}"
	}

	# Request body parameters
	data = {
		"grant_type": "client_credentials",
		"scope": request_scope
	}

	try:
		response = requests.post(url, headers=headers, data=data)
		response.raise_for_status()  # Raises an exception for HTTP error codes

		return response.json()  # Token response is returned as JSON
	except requests.exceptions.RequestException as e:
		print(f"Error getting token: {e}")
		return None

class TokenManager:
	def __init__(self):
		self._token_data = None

	def get_valid_token(self):
		"""Returns a valid token, either from cache or by requesting a new one"""
		if self._is_token_valid():
			print("Using existing valid token")
			return self._token_data

		print("Requesting new access token...")
		self._token_data = get_access_token()
		return self._token_data

	def _is_token_valid(self):
		"""Checks if the current token is valid and not expired"""
		if not self._token_data:
			return False

		expiration_timestamp = time.time() + self._token_data["expires_in"]
		return time.time() < (expiration_timestamp - 60)  # 60-second buffer

# Modify dnb_company_search to use TokenManager
def dnb_company_search(token_manager, company_name="Demo AB", company_address="SE"):
	token = token_manager.get_valid_token()
	if not token:
		print("Failed to get valid token")
		return None

	headers = {
		"Authorization": f"Bearer {token['access_token']}",
		"Content-Type": "application/json",
		"Accept": "application/json"
	}

	search_request = {
		"name": company_name,
		"country": company_address
	}

	url = "https://sandbox-api.bisnode.com/credit-data-companies/v2/companies"

	response = requests.post(url, headers=headers, json=search_request)
	if response.status_code == 200:
		data = response.json()
		print("API response:", data)
		return data
	else:
		print("Error:", response.status_code, response.text)
		return None

# Validates if the search responds with a single company
# Returns True if a single company is found, False if zero or multiple companies are found
def task_two_validate_response(search_response):
	search_response = search_response["companies"]
	if len(search_response) == 0:
		print("No companies found")
		return False
	elif len(search_response) == 1:
		print("One company found")
		return True
	else:
		print("Multiple companies found")
		return False

def task_two_endpoint(name, city, state):

        url = "https://qfstagingservices.azurewebsites.net/api/v1/Account/DnBFindCompany"
        params = {
                "name": "Alta Equipment",
                "city": "New Hudson",
                "state": "MI",
        }

        response = requests.post(url, json=params)
        response.raise_for_status()
        return response.json()
def dnb_validate_search_response(search_response):
	search_response = search_response["companies"]
	if len(search_response) == 0:
		print("No companies found")
		return -1
	elif len(search_response) == 1:
		print("One company found")
		return 1
	else:
		print("Multiple companies found")
		return 0

def task_two(vendor_id):
    try:
        # Get vendor information
        vendor = db_driver.get_vendor_by_id(vendor_id)
        if not vendor:
            print(f"Vendor with ID {vendor_id} not found")
            return None

        vendor_name = vendor["Name"]
        vendor_city = {vendor['City']}
        vendor_state = vendor["State"]
        response = task_two_endpoint(vendor_name, vendor_city, vendor_state)
        validated = task_two_validate_response(response)

        if validated == -1:
            update_success = db_driver.update_flags(vendor_id, "DNB - No company found")
            if not update_success:
                print(f"Failed to update flags for vendor {vendor_id}")
            return {
                "validated": validated,
                "message": "No companies found in DNB search"
            }




    except Exception as e:
        print(f"Operation failed: {str(e)}")
        return False












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
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            #"model": "llama-3.1-sonar-small-128k-online",
            "model": "sonar",

            "messages": [
                {
                    "role": "system",
                    "content": "Be precise and concise."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "return_citations": True,
            "stream": False
        }

        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            # Print detailed error information
            print(f"Perplexity API Error Details:")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"Response Body: {response.text}")
            print(f"Request Headers: {headers}")
            print(f"Request Data: {data}")
            
            return json.dumps({
                "found": False,
                "registration_date": None,
                "years_in_business": None,
                "status": None,
                "explanation": f"API error: {response.status_code} - {response.text}"
            })

    except Exception as e:
        print(f"Error calling Perplexity API: {str(e)}")
        return json.dumps({
            "found": False,
            "registration_date": None,
            "years_in_business": None,
            "status": None,
            "explanation": f"Error calling Perplexity API: {str(e)}"
        })

def get_state_sos_url(state):
    """
    Get the Secretary of State URL for a given state from the CSV file.

    Args:
        state (str): State name (can be in any case)

    Returns:
        str: URL for the state's Secretary of State website, or None if not found
    """
    try:
        # Get the path to the CSV file - fix the path resolution
        current_dir = Path(__file__).parent.parent
        csv_path = current_dir / "secretary_of_state_lookup.csv"
        
        # Debug print to verify the path
        print(f"Looking for CSV at: {csv_path}")
        print(f"CSV exists: {csv_path.exists()}")

        # Read the CSV file
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            # Convert state to title case for comparison (e.g., "new york" -> "New York")
            state_title = state.title()

            # Search for the state in the CSV
            for row in reader:
                if row['state'].lower() == state.lower():
                    print(f"Found URL for state {state}: {row['url']}")
                    return row['url']

            # If state not found
            print(f"State '{state}' not found in Secretary of State lookup table")
            return None

    except Exception as e:
        print(f"Error reading Secretary of State URL for {state}: {str(e)}")
        return None

async def check_secretary_of_state(vendor_name, state):
    """
    Use Playwright to scrape Secretary of State website and Perplexity AI to analyze the content.

    Args:
        vendor_name (str): Name of the vendor to check
        state (str): State name (e.g., "New York")

    Returns:
        dict: Results including found status, years in business, and active status
    """
    try:
        # Get the appropriate Secretary of State URL
        sos_url = get_state_sos_url(state.lower())
        if not sos_url:
            return {"error": f"No Secretary of State URL found for {state}"}

        # Use Playwright to scrape the website
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            try:
                # Navigate to the Secretary of State website
                await page.goto(sos_url)
                
                # Wait for the search form to be visible
                await page.wait_for_selector('input[type="text"]', timeout=10000)
                
                # Enter the vendor name in the search field
                await page.fill('input[type="text"]', vendor_name)
                
                # Click the search button
                await page.click('button[type="submit"]')
                
                # Wait for results to load
                await page.wait_for_selector('.search-results', timeout=10000)
                
                # Get the HTML content of the results
                html_content = await page.content()
                
            except Exception as e:
                print(f"Error scraping website: {str(e)}")
                return {
                    "error": f"Error scraping website: {str(e)}",
                    "flags": ["Error accessing Secretary of State website"],
                    "flag_count": 1
                }
            finally:
                await browser.close()

        # Create a prompt for Perplexity to analyze the HTML content
        prompt = f"""
        I have scraped the Secretary of State website for a business search. Here is the HTML content:

        {html_content}

        Please analyze this content and extract the following information:
        1. Is the business found in the registry? (Yes/No)
        2. When was the business registered? (date)
        3. How many years has the business been operating? (calculate from registration date to today)
        4. What is the current status of the business? (Active, Inactive, etc.)
        5. Is the status "Active" or equivalent? (Yes/No)

        Return your findings in this JSON format:
        {{
            "found": true/false,
            "registration_date": "MM/DD/YYYY" or null,
            "years_in_business": number or null,
            "status": "status text" or null,
            "active": true/false,
            "explanation": "brief explanation of findings"
        }}
        """

        # Call Perplexity API
        perplexity_response = call_perplexity_api(prompt)
        
        # Parse the response
        try:
            results = json.loads(perplexity_response)
        except json.JSONDecodeError:
            print(f"Invalid JSON response from Perplexity: {perplexity_response}")
            return {
                "found": False,
                "registration_date": None,
                "years_in_business": None,
                "status": None,
                "active": False,
                "explanation": "Error parsing Perplexity response",
                "flags": ["Error parsing Secretary of State results"],
                "flag_count": 1
            }

        # Determine if any flags should be set based on the criteria
        flags = []
        if not results.get("found", False):
            flags.append("Business not found in registry")
        elif results.get("years_in_business") is not None and results["years_in_business"] < 5:
            flags.append(f"Business operating for only {results['years_in_business']} years")
        elif results.get("status") is not None and not results.get("active", False):
            flags.append(f"Business status is '{results['status']}' instead of 'Active'")

        results["flags"] = flags
        results["flag_count"] = len(flags)

        return results

    except Exception as e:
        return {
            "error": str(e),
            "flags": ["Error checking Secretary of State"],
            "flag_count": 1
        }



async def task_three(vendor_id):
    """
    Checks the vendor in their state's official business registry (Secretary of State).
    Adds flags if:
    - Business has been operating for less than 5 years
    - Business status is not "Active"
    - Business is not found in the registry
    
    Args:
        vendor_id (str): The vendor ID to check
        
    Returns:
        dict: Results of the check including any flags raised
    """
    try:
        # Get vendor information
        vendor = db_driver.get_vendor_by_id(vendor_id)
        if not vendor:
            print(f"Vendor with ID {vendor_id} not found")
            return None
            
        vendor_name = vendor["Name"]
        vendor_state = vendor["State"]
        
        # Check the vendor in the Secretary of State registry
        sos_results = await check_secretary_of_state(vendor_name, vendor_state)
        
        # Process results and update vendor record
        if "error" in sos_results:
            # Handle error case
            print(f"Error checking Secretary of State: {sos_results['error']}")
            db_driver.update_flags(vendor_id, "Error checking Secretary of State")
            return {
                "success": False,
                "message": sos_results["error"]
            }
        
        # Update SOS info in the database
        years_in_business = sos_results.get("years_in_business")
        active_status = sos_results.get("active", False)
        
        # Update the database with SOS information
        db_driver.update_sos_info(vendor_id, years_in_business, active_status)
        
        # Add flags based on the criteria
        flags_added = []
        
        if not sos_results.get("found", False):
            flag = "Business not found in Secretary of State registry"
            db_driver.update_flags(vendor_id, flag)
            flags_added.append(flag)
        elif years_in_business is not None and years_in_business < 5:
            flag = f"Business operating for only {years_in_business} years"
            db_driver.update_flags(vendor_id, flag)
            flags_added.append(flag)
        elif not active_status:
            status = sos_results.get("status", "Unknown")
            flag = f"Business status is '{status}' instead of 'Active'"
            db_driver.update_flags(vendor_id, flag)
            flags_added.append(flag)
        
        return {
            "success": True,
            "vendor_name": vendor_name,
            "state": vendor_state,
            "found": sos_results.get("found", False),
            "years_in_business": years_in_business,
            "active": active_status,
            "flags_added": flags_added,
            "flag_count": len(flags_added)
        }
        
    except Exception as e:
        print(f"Operation failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }








def task_four():
     pass

def call_perplexity_dict(prompt):
    """ Calls the Perplexity API on the prompt input.

    Args:
        prompt (str): The prompt Perplexity is given

    Returns:
        dict: Data returned by Perplexity

    """
    url = "https://api.perplexity.ai/chat/completions"
    api_key = PERPLEXITY_API_KEY

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "You are a business verification agent. Your job is to validate business listing and address consistency and return raw JSON with boolean flags."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()["choices"][0]["message"]["content"]
        match = re.search(r'\{[\s\S]*?\}', result)
        if match:
            json_block = match.group(0)
            return json.loads(json_block)
        else:
            raise ValueError("No valid JSON object found in response.")
    else:
        print("Error:", response.status_code)
        print(response.text)

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
    prompt = f"""Please search for the business {vendor_name} {vendor_address} on Google.

            1. Is a Google Business listing with an address found?
            2. Does this address match the address {vendor_address}?
            3. Does the business have a website listed?
            4. Is the site accessible with an address listed on the homepage or contact page, and
                do any of the locations lised match the address {vendor_address}?

            Respond in JSON in the following format:
            {{
                "google_business_found": true/false,
                "google_address_match": true/false,
                "website_found": true/false,
                "website_address_found": true/false,
                "website_address_match": true/false
            }}"""
    try:
        # Input this prompt to Perpexity and parse the response
        response = call_perplexity_dict(prompt)

        # Flag for no business found, no website found, no address listed, or mismatched addresses
        flags = []
        if not response["google_business_found"]:
            flags.append("No Google business listing found")
        elif not response["google_address_match"]:
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
            return ["Address does not appear to be a physical building."]

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
                if "establishment" not in types and "point_of_interest" not in types and "premise" not in types and "street_address" not in types:
                    return ["Address does not appear to a business establishment."]
                # If the location type corresponds to a PO box, flag
                if "post_office" in types or "mailbox" in types:
                    print("B")
                    return ["Address appears to be a P.O. box or mail drop."]
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
    flags = address_website_flags + maps_flags
    num_flags += len(maps_flags)

    # Increment flags
    for flag in flags:
        result = db_driver.update_flags(vendor_id, flag)
        if not result:
            print(f"Failed to update flags for vendor id {vendor_id}")

    return {
        "flags": flags,
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
    prompt = f"""Search for serious adverse news related to the business {vendor_name} combined with any of the following terms: {', '.join(keywords)}.

    Specifically, only raise flags if there are credible reports in the top five results of the vendor being:
    - Found guilty or settled in lawsuits involving fraud or serious financial misconduct
    - Shut down, declared bankruptcy, or lost licenses to operate
    - Involved in government enforcement actions or fines exceeding $500,000
    - The subject of widely reported scandals that caused reputational or financial damage

    Do not raise flags for:
    - Minor lawsuits or settlements
    - Routine regulatory inspections or technical violations
    - Public controversies unless they had major legal or financial consequences

    If this company is a large, established corporation (e.g. a Fortune 500 company), be less sensitive in flagging - do not include common lawsuits or resolved class actions that are typical for large companies.

    If this company is a small business or startup, be more sensitive.

    Ignore isolated incidents involving individual employees unless the company itself was found responsible or the impact was significant.

    Ignore incidents that are 20+ years ago, unless they have a clear bearing on the company's current status, reputation, or operations.

    Return a JSON object in the following format:
    {{
      "adverse_findings": true/false,
      "flag_reasons": ["List of short descriptions of adverse finding such as 'Bankruptcy filing in 2020' or 'Lawsuit from partner'"]
    }}"""
    try:
        # Call Perplexity on the prompt
        response = call_perplexity_dict(prompt)

        # Raise flags
        if not response["adverse_findings"]:
            return {"flags": [], "num_flags": 0}
        num_flags = len(response["flag_reasons"])

        for flag in response["flag_reasons"]:
            result = db_driver.update_flags(vendor_id, flag)
            if not result:
                print(f"Failed to update flags for vendor id {vendor_id}")

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
            recipient_email = os.getenv("test_email_recipient")
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

def task_seven_flag_report(vendor_id):
        try:
            # Get vendor information
            vendor = db_driver.get_vendor_by_id(vendor_id)
            if not vendor:
                print(f"Vendor with ID {vendor_id} not found")
                return None

            vendor_name = vendor["Name"]
            vendor_address = f"{vendor['Street']}, {vendor['City']}, {vendor['State']}, {vendor['ZIP']}"

            # Get flags information
            flags_info = db_driver.get_flags(vendor_id)
            if not flags_info:
                print(f"No flags found for vendor {vendor_id}")
                return None

            flag_summary = "\n".join([f"- {flag}" for flag in flags_info["Flags"]])

            body = f"Vendor Name: {vendor_name}\nVendor Address: {vendor_address}\n\nSummary of Flags:\n{flag_summary}"
            send_email(body, vendor_name)



        except Exception as e:
            print(f"Operation failed: {str(e)}")
            return False

task_seven_flag_report("V101")
