import pytest
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from AI.tasks import task_one, task_two, task_seven
from db import DatabaseDriver

# Load environment variables
load_dotenv()

# Initialize database driver
db_driver = DatabaseDriver()

@pytest.fixture
def test_vendor_id():
    """Returns a valid vendor ID from the database"""
    vendors = db_driver.get_vendors()
    if not vendors:
        pytest.skip("No vendors available in database")
    return vendors[0]["ID"]

@pytest.fixture
def test_account_id():
    """Returns a valid account ID from the database"""
    accounts = db_driver.get_accounts()
    if not accounts:
        pytest.skip("No accounts available in database")
    return accounts[0]["ID"]

class TestTaskOne:
    def test_task_one_with_valid_ids(self, test_vendor_id, test_account_id):
        """Test task_one with valid vendor and account IDs"""
        result = task_one(test_account_id, test_vendor_id)
        
        assert result is not None
        assert "matches_found" in result
        assert "data" in result
        assert isinstance(result["matches_found"], bool)
        assert isinstance(result["data"], dict)
        
        # Verify data structure
        required_fields = [
            "Account.Name", "Account.Address",
            "Vendor.Name", "Vendor.Address", "Vendor.Website"
        ]
        for field in required_fields:
            assert field in result["data"]

    def test_task_one_with_invalid_vendor(self, test_account_id):
        """Test task_one with invalid vendor ID"""
        result = task_one(test_account_id, "nonexistent_vendor")
        assert result is None

    def test_task_one_with_invalid_account(self, test_vendor_id):
        """Test task_one with invalid account ID"""
        result = task_one("nonexistent_account", test_vendor_id)
        assert result is None

class TestTaskTwo:
    def test_task_two_with_valid_vendor(self, test_vendor_id):
        """Test task_two returns valid response structure"""
        result = task_two(test_vendor_id)
        
        assert result is not None
        assert isinstance(result, dict)
        assert "validated" in result
        assert "message" in result
        assert isinstance(result["validated"], bool)
        assert isinstance(result["message"], str)
        
        # If validated is True, we know it must be single company case
        if result["validated"] is True:
            assert result["message"] == "Single company found in DNB database"

    def test_task_two_with_invalid_vendor(self):
        """Test task_two with invalid vendor ID"""
        result = task_two("nonexistent_vendor")
        assert result is None

    def test_task_two_endpoint_response(self, test_vendor_id):
        """Test task_two_endpoint function specifically"""
        vendor = db_driver.get_vendor_by_id(test_vendor_id)
        if not vendor:
            pytest.skip("Could not get vendor details")
            
        from AI.tasks import task_two_endpoint
        response = task_two_endpoint(
            vendor["Name"],
            vendor["City"],
            vendor["State"]
        )
        
        assert isinstance(response, dict)
        assert "isSuccess" in response
        assert isinstance(response["isSuccess"], bool)
        
        if response["isSuccess"]:
            assert "dnbCompanies" in response
            assert isinstance(response["dnbCompanies"], list)
        else:
            assert "message" in response

    def test_task_two_api_failure(self, test_vendor_id):
        """Test task_two when DNB API call fails"""
        result = task_two(test_vendor_id)
        
        if result is not None and not result["validated"]:
            assert isinstance(result["message"], str)

class TestTaskSeven:
    def test_task_seven_with_valid_vendor_and_flags(self, test_vendor_id):
        """Test task_seven when vendor has flags"""
        # First ensure the vendor has some flags
        
        # Get flags to verify they exist
        flags_info = db_driver.get_flags(test_vendor_id)
        if not flags_info or flags_info["NumFlags"] == 0:
            pytest.skip("Could not set up flags for testing")
        
        result = task_seven(test_vendor_id)
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["message"] == "Email sent successfully"

    def test_task_seven_with_invalid_vendor(self):
        """Test task_seven with invalid vendor ID"""
        result = task_seven("nonexistent_vendor")
        assert result is None

    def test_task_seven_with_no_flags(self, test_vendor_id):
        """Test task_seven behavior when vendor has no flags"""
        # First ensure the vendor has no flags
        flags_info = db_driver.get_flags(test_vendor_id)
        if flags_info and flags_info["NumFlags"] > 0:
            pytest.skip("Vendor already has flags, cannot test no-flags scenario")
        
        result = task_seven(test_vendor_id)
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["message"] == "No flags found for vendor"

def test_email_configuration():
    """Test that required email environment variables are set"""
    required_vars = [
        "sender_email_address",
        "sender_email_api_pass",
        "smtp_server",
        "smtp_port",
        "test_email_recipient"
    ]
    
    for var in required_vars:
        assert os.getenv(var) is not None, f"Missing required environment variable: {var}"