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
import email.utils

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
- Connects to the DNB API

**What AI looks for**:

- **Prescreen Score**:
    - If "High Risk" → flag
- **Headquarters Address**:
    - Save this address as `DNBaddress` to determine which state's Secretary of State website to use in the next step

**Data Used Later**:

- `DNBaddress.state` → to find correct Secretary of State lookup URL

"""

# Validates if the search responds with a single company
# Returns True if a single company is found, False if zero or multiple companies are found
"""def task_two_validate_response(search_response):
	search_response = search_response["companies"]
	if len(search_response) == 0:
		print("No companies found")
		return False
	elif len(search_response) == 1:
		print("One company found")
		return True
	else:
		print("Multiple companies found")
		return False"""

def task_two_endpoint(name, city, state, country=None):
    """
    Makes API request to DNB endpoint with country-specific formatting.

    Args:
        name (str): Vendor name
        city (str): Vendor city
        state (str): Vendor state
        country (str, optional): Country code, used for non-US vendors

    Returns:
        dict: API response
    """
    url = "https://qfstagingservices.azurewebsites.net/api/v1/Account/DnBFindCompany"

    # Build params based on country
    params = {
        "name": name,
        "city": city,
        "state": state,
    }

    # Add country param for Canadian vendors
    if country == "CA":
        params["country"] = country

    response = requests.post(url, json=params)
    response.raise_for_status()
    return response.json()

def task_two_validate_response(search_response):
	search_response = search_response.get("dnbCompanies", [])
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
    """
    Performs validation of vendors using DNB database.

    Args:
        vendor_id (str): The vendor ID to validate

    Returns:
        dict: Results of the validation including any flags
    """
    try:
        # Get vendor information
        vendor = db_driver.get_vendor_by_id(vendor_id)
        if not vendor:
            print(f"Vendor with ID {vendor_id} not found")
            return None

        # Get vendor's country
        vendor_country = db_driver.get_vendor_country(vendor_id)
        if not vendor_country:
            print(f"Could not determine country for vendor {vendor_id}")
            return None

        # Make API call with country-specific parameters
        response = task_two_endpoint(
            name=vendor["Name"],
            city=vendor["City"],
            state=vendor["State"],
            country=vendor_country if vendor_country == "CA" else None
        )

        if response["isSuccess"] == False:
            update_success = db_driver.update_flags(vendor_id, "DNB - API call failed")
            return {
                "validated": False,
                "message": "DNB API call failed"
            }

        # Handle both successful cases
        if "dnbCompanies" in response:
            # Validate number of companies found
            validation_result = task_two_validate_response(response)

            if validation_result == 1:
                # Exactly one company found
                return {
                    "validated": True,
                    "message": "Single company found in DNB database"
                }
            elif validation_result == 0:
                # Multiple companies found
                update_success = db_driver.update_flags(vendor_id, "DNB - Multiple companies found in database")
                return {
                    "validated": False,
                    "message": "Multiple companies found in DNB database"
                }
        else:
            # No company found but API call was successful
            update_success = db_driver.update_flags(vendor_id, "DNB - Successful search - No company found")
            return {
                "validated": False,
                "message": "No companies found in DNB search"
            }

    except Exception as e:
        print(f"Operation failed: {str(e)}")
        return None












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
    Get the Secretary of State URL for a given state using the database lookup.

    Args:
        state (str): State name (can be in any case)

    Returns:
        str: URL for the state's Secretary of State website, or None if not found
    """
    try:
        # Format state name to lowercase and remove spaces
        formatted_state = state.lower().replace(" ", "")

        # Get URL from database
        url = db_driver.get_state_link(formatted_state)

        if url:
            print(f"Found URL for state {state}: {url}")
            return url
        else:
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

def check_ofac_sanctions_list(vendor_name):
    """
    Uses Selenium to check the OFAC Sanctions List for the vendor name.
    Sets the minimum score to 80 as required.

    Args:
        vendor_name (str): Name of the vendor to check

    Returns:
        bool: True if a match is found, False otherwise
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    try:
        # Set up Chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # Initialize the driver with webdriver-manager
        driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=chrome_options)
        driver.set_page_load_timeout(30)  # Set page load timeout
        wait = WebDriverWait(driver, 20)  # Set explicit wait timeout

        try:
            # Navigate to the OFAC Sanctions List search page
            driver.get("https://sanctionssearch.ofac.treas.gov/")

            # Wait for and find the name input field
            name_input = wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_MainContent_txtLastName"))
            )
            name_input.send_keys(vendor_name)

            # Set the slider value to 80 using JavaScript
            # First, locate the hidden input that stores the slider value
            slider_input = wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_MainContent_Slider1"))
            )

            # Also find the visible bound control that shows the value
            bound_control = wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_MainContent_Slider1_Boundcontrol"))
            )

            # Use JavaScript to set both values to 80
            driver.execute_script("arguments[0].value = '80';", slider_input)
            driver.execute_script("arguments[0].value = '80';", bound_control)

            # Click the search button
            search_button = wait.until(
                EC.element_to_be_clickable((By.ID, "ctl00_MainContent_btnSearch"))
            )
            search_button.click()

            # Wait for results to load
            results_text = wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_MainContent_lblResults"))
            ).text

            print(f"Results text: {results_text}")

            # Parse the number of results found
            match = re.search(r'Lookup Results: (\d+) Found', results_text)
            if match:
                match_count = int(match.group(1))
                print(f"Found {match_count} matches")
                return match_count > 0
            else:
                print("No match count found in results text")
                # Check if there are any results in the table
                results_table = driver.find_elements(By.CSS_SELECTOR, '#scrollResults table tr')
                return len(results_table) > 0

        except TimeoutException as e:
            print(f"Timeout during OFAC search: {str(e)}")
            return True  # Be cautious and return True to trigger manual review

        except Exception as e:
            print(f"Error during OFAC search: {str(e)}")
            return True  # Be cautious and return True to trigger manual review

        finally:
            driver.quit()

    except WebDriverException as e:
        print(f"Error initializing browser: {str(e)}")
        return True  # Be cautious and return True to trigger manual review

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return True  # Be cautious and return True to trigger manual review

def task_four(vendor_id):
    """
    Performs OFAC Sanctions List check for a vendor.
    Adds a flag if the vendor name appears on the OFAC Sanctions List.

    Args:
        vendor_id (str): The vendor ID to check

    Returns:
        dict: Results of the check including whether a match was found
    """
    try:
        # Get vendor information
        vendor = db_driver.get_vendor_by_id(vendor_id)
        if not vendor:
            print(f"Vendor with ID {vendor_id} not found")
            return None

        vendor_name = vendor["Name"]

        # Check the OFAC sanctions list
        match_found = check_ofac_sanctions_list(vendor_name)

        # Update the database with OFAC information
        db_driver.update_ofac_info(vendor_id, match_found)

        # Add flag if a match was found
        if match_found:
            flag = "Vendor found on OFAC Sanctions List"
            db_driver.update_flags(vendor_id, flag)

            return {
                "success": True,
                "vendor_name": vendor_name,
                "match_found": True,
                "flags_added": [flag],
                "flag_count": 1
            }

        return {
            "success": True,
            "vendor_name": vendor_name,
            "match_found": False,
            "flags_added": [],
            "flag_count": 0
        }

    except Exception as e:
        print(f"Operation failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

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
        "temperature": 0.2,
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

    vendor_name = vendor_info["Name"]

    vendor_address = f"{vendor_info['Street']}, {vendor_info['City']}, {vendor_info['State']}, {vendor_info['ZIP']}"

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
    vendor_name = vendor_info["Name"]

    # Create a prompt to search for adverse news associated with the vendor
    keywords = ["fraud", "lawsuit", "shutdown", "bankruptcy", "charges", "scam", "indictment", "settlement", "scandal"]
    prompt = f"""Search for serious adverse news related to the business {vendor_name} combined with each of the following terms: {', '.join(keywords)}.

    Only raise flags if credible sources in the top 10 search results report the vendor was:
    - Fined by a government agency over $500,000
    - Involved in a settlement or ruling involving fraud, bribery, antitrust, or foreign corrupt practices (FCPA)
    - Created a bankruptcy trust to shield liabilities (e.g., for asbestos or similar claims)
    - Was the subject of ongoing government lawsuits involving antitrust, securities fraud, or consumer protection
    - Penalized by major regulators (e.g., FTC, SEC, CNIL, EPA) for serious misconduct

    Do not raise flags for:
    - Lawsuits without major financial or reputational consequence
    - Routine product recalls, OSHA violations, or technical regulatory infractions
    - Incidents under $500k unless part of a larger scandal
    - Historical incidents (20+ years ago) unless they clearly affect the company’s current operations or public trust

    Treat large public companies more leniently — only flag if the issue is unusually severe (e.g., FCPA, antitrust, multimillion-dollar fines).

    Ignore isolated incidents involving individual employees unless the company itself was found responsible or the impact was significant.

    Ignore incidents that are 20+ years ago, unless they have a clear bearing on the company's current status, reputation, or operations.

    Training examples:

    For John Deere, might raise flags for
    1. Settlement of $10 million in 2024 for FCPA violations, involving bribery by subsidiary Wirtgen Thailand from 2017-2020
    2. Antitrust lawsuit filed in 2025 by FTC and multiple state attorneys general alleging unlawful repair monopoly and anti-competitive practices.

    For Altec Inc., might raise no flags.

    For Paccar Inc., might raise no flags.

    For United Rentals, might raise flags for
    1. SEC civil fraud charges settled by United Rentals for $14 million related to improper accounting and fraudulent transactions (2000–2002)
    2. United Rentals permanently enjoined from violating federal securities laws as part of settlement
    3. Widespread reporting of financial fraud and SEC enforcement action involving senior executives


    Return a JSON object in the following format:
    {{
      "adverse_findings": true/false,
      "flag_reasons": ["List of short descriptions of adverse finding such as 'Bankruptcy filing in 2020' or 'Lawsuit from partner'. Less than 20 words each."]
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
        body (str): Body content of the email
        vendor_name (str): Name of vendor for subject line
        recipient_email (str, optional): Email address of recipient. If None, uses EMAIL_RECIPIENT from env

    Returns:
        bool: True if email sent successfully, False otherwise

    Raises:
        ValueError: If no recipient email is provided and EMAIL_RECIPIENT not set
        SMTPException: If SMTP connection or sending fails
    """
    try:
        # Email configuration
        sender_email = os.getenv("sender_email_address")
        sender_password = os.getenv("sender_email_api_pass")
        smtp_server = os.getenv("smtp_server", "smtp.gmail.com")
        smtp_port = int(os.getenv("smtp_port", "587"))

        # Validate required email configuration
        if not all([sender_email, sender_password, smtp_server, smtp_port]):
            raise ValueError("Missing required email configuration")

        # Use default recipient if none provided
        if recipient_email is None:
            recipient_email = os.getenv("test_email_recipient")
            if not recipient_email:
                raise ValueError("No recipient email provided and EMAIL_RECIPIENT not set in environment")

        # Validate email addresses
        if not all(map(lambda x: '@' in x and '.' in x, [sender_email, recipient_email])):
            raise ValueError("Invalid email address format")

        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = f"Vendor Due Diligence Flags - {vendor_name}"
        message["Date"] = email.utils.formatdate(localtime=True)

        # Add body with proper encoding
        message.attach(MIMEText(body, "plain", "utf-8"))

        # Create SMTP session with timeout
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()  # Enable TLS
            server.login(sender_email, sender_password)
            server.send_message(message)

        return True

    except (smtplib.SMTPException, ValueError) as e:
        print(f"Failed to send email: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error sending email: {str(e)}")
        return False

def task_seven(vendor_id):
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
                return None


            if flags_info["NumFlags"] > 0 :

                flag_summary = "\n".join([f"- {flag}" for flag in flags_info["Flags"]])

                body = f"Vendor Name: {vendor_name}\nVendor Address: {vendor_address}\n\nSummary of Flags:\n{flag_summary}"
                send_email(body, vendor_name)
            else:
                return {
                    "success": True,
                    "message": "No flags found for vendor"
                }

            return {
                "success": True,
                "message": "Email sent successfully"
            }


        except Exception as e:
            print(f"Operation failed: {str(e)}")
            return False
