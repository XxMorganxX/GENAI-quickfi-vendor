from db import DatabaseDriver

db_driver = DatabaseDriver()


"""
Flagged object wrapper
- If a certain company should be flagged as a risk, we can wrap it in a FlaggedObject
- This will allow us to easily check if the object should be flagged and to store the reason for flagging
"""



"""
Task 1 - Check Notion

- How should we store the flagging vendors?
- Replace raise "flaggedobject" with the flagging logic
"""
def task_one(account_id, vendor_id):
    try:
        # Use DatabaseDriver directly instead of HTTP request
        data = db_driver.due_diligence_check(account_id, vendor_id)
        if data is None:
            raise ValueError(f"Account {account_id} not found")
        
        vendor_name, vendor_address = data["Vendor.Name"], data["Vendor.Address"]
        account_name, account_address = data["Account.Name"], data["Account.Address"]
        
        if vendor_name == account_name:
                raise "FlaggedObject"
        
        if vendor_address == account_address:
                raise "FlaggedObject"
        
    
    except Exception as e:
        print(f"Database operation failed: {str(e)}")
        raise