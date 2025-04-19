# GenAI QuickFi Vendor Validation

This project is an AI-powered due diligence tool that automates the validation of vendor information for QuickFi. It checks public data sources and web results to confirm vendors are real, active businesses and flag potential business risks. 

## Project Structure 
```
GENAI-quickfi-vendor/
├── AI/                           
│   ├── task_documentation.txt         # Documentation of AI/ML tasks
|   ├── tasks.py                       # Core implementation of validation tasks 
│   └── tests/                         # Test suite for AI/ML codebase
├── app.py                             # API endpoints
├── db.py                              # Back-end database logic  
├── secretary_of_state_lookup.csv      # CSV file used for company validation
```
Core Workflow Files: 
- `app.py`: Flask server providing API endpoints for data retrieval and flag updates.
- `db.py`: Database interface for interacting with Supabase tables such as Vendor, Account, and Equipment.
- `AI/tasks.py`: Core business logic implementing the due diligence tasks. Each function corresponds to a validation step (e.g. Google Maps check, OFAC screening, adverse news search).
- `secretary_of_state_lookup.csv`: Static reference table mapping U.S. states to their Secretary of State business search URLs.

## Features
### Entity Matching and Data Consistency
- Compares vendor and account names and addresses to determine if they are likely the same entity.
- Flags if names or addresses match exactly.
### Business Identity Verification
- Searches the Dun & Bradstreet (DNB) database using vendor name and address.
- Flags if no matching business is found or if multiple results are returned.
- Extracts state information from DNB results to support downstream checks.
### Government Registration and Status Checks
- Validates vendor registration using Secretary of State business registries based on the identified state.
- Flags if the business is inactive, too recently registered (less than five years old), or not found in the registry.
### Online and Physical Presence Validation
- Uses Google Search and Google Maps to verify whether a business has a Google listing, a website, and a valid physical address.
- Flags missing or inconsistent address information, lack of business listing, or addresses that appear to be non-commercial (e.g., vacant lots or P.O. boxes).
### Adverse News Detection
- Uses Perplexity AI to identify serious adverse news involving the vendor, such as fraud, major government fines, bankruptcy, or reputational scandals.
### Summary Report Generation
- Compiles all validation results and generates a summary report.
- Sends an email containing vendor details and all flags raised to a configured recipient.

## Requirements

### Python Packages

Install dependencies using `pip install -r requirements.txt`.

To install Playwright dependencies:
```bash
playwright install
```

### Required API Keys and Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Supabase
projecturl=your_supabase_project_url
anonkey=your_supabase_anon_key

# API Integrations
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
perplexity_api_key=your_perplexity_api_key

# Email (for task 7 reporting)
sender_email_address=your_email_address
sender_email_api_pass=your_app_password
test_email_recipient=recipient_email@example.com
smtp_server=your_server
smtp_port=your_port
```

---
## Code and Documentation Standards

To ensure consistency across contributions and maintainability over time:

- Follow the file organization pattern already established (API in `app.py`, logic in `AI/tasks.py`, DB access in `db.py`).
- All vendor-related data access should go through `DatabaseDriver` in `db.py`.
- Task functions in `AI/tasks.py` should:
  - Accept a `vendor_id` or `account_id`
  - Return structured dictionaries including flags and result summaries
  - Use `db_driver.update_flags(...)` to record issues
- Use environment variables for all credentials and API keys.

If contributing, functions should be documented with a clear docstring explaining inputs, outputs, and failure modes.
