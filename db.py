from datetime import date
from supabase import create_client, Client
from sqlalchemy.dialects.postgresql import ARRAY
import os
import flask
from flask import Flask, request, jsonify


# Initialize Supabase client
PROJECTURL = os.getenv("projecturl")
ANONKEY = os.getenv("anonkey")
supabase: Client = create_client(PROJECTURL, ANONKEY)

class DatabaseDriver:
    """
    Database driver for interacting with Supabase.
    Handles reading and writing information with the Supabase database.
    """

    def get_account_by_id(self, account_id=None):
        """
        Fetches account information by account ID from Supabase.
        """
        try:
            print(f"Attempting to fetch account with ID: {account_id}")
            response = supabase.table("Account").select("*").eq("ID", account_id).execute()
            print(f"Response: {response}")
                
            if not response.data:
                return None
                
            account = response.data[0]
            print(f"Found account: {account}")
            
            try:
                equipment_response = supabase.table("Equipment").select("*").eq("AccountID", account_id).execute()
                if equipment_response.error:
                    print(f"Error fetching equipment: {equipment_response.error}")
                    account["Equipment"] = []
                else:
                    account["Equipment"] = equipment_response.data if equipment_response.data else []
            except Exception as e:
                print(f"Error fetching equipment: {str(e)}")
                account["Equipment"] = []
                
            return account
        except Exception as e:
            print(f"Unexpected error in get_account_by_id: {str(e)}")
            return None
        

    def get_equipment_by_account_id(self, account_id):
        """
        Fetches equipment information by account ID from Supabase.
        """
        response = supabase.table("Equipment").select("*").eq("AccountID", account_id).execute()
        return response.data if response.data else []


    def due_diligence_check(self, account_id, vendor_id):
        """
        Performs a due diligence check for a vendor associated with an account.
        Returns a dictionary containing:
        - Account information
        - Vendor information
        - Vendor's flags and flags added
        """
        try:
            
            # Get account information
            account = self.get_account_by_id(account_id)
            if not account:
                return None

            # Get vendor information
            vendor = self.get_vendor_by_id(vendor_id)
            if not vendor:
                return None

            result = {
                "Account.Name": account.Name,
                "Account.Address": f"{account.Street}, {account.City}, {account.State}, {account.ZIP}",
                "Vendor.Name": vendor.Name,
                "Vendor.Address": f"{vendor.Street}, {vendor.City}, {vendor.State}, {vendor.ZIP}",
                "Vendor.Website": vendor.Website    
            }
            return result
        except Exception as e:
            print(f"Error in due diligence check: {str(e)}")
            return None

    def update_flags(self, vendor_id, flag):
        """
        Updates the number of flags for a vendor and the date the vendor was scanned.
        """
        try:
            # First check if vendor exists
            vendor_response = supabase.table("Vendor").select("*").eq("ID", vendor_id).execute()
            if not vendor_response.data:
                return False

            vendor = vendor_response.data[0]
            flags_added = vendor.get("FlagsAdded", [])
            flags_added.append(flag)

            # Update the vendor
            update_response = supabase.table("Vendor").update({
                "FlagsAdded": flags_added,
                "Flags": vendor.get("Flags", 0) + 1,
                "DateScanned": str(date.today())
            }).eq("ID", vendor_id).execute()

            # If we get data back in the response, the update was successful
            return bool(update_response.data)
        except Exception as e:
            print(f"Error updating flags: {str(e)}")
            return False

    def get_flags(self, vendor_id):
        """
        Fetches flags for a vendor.
        """
        try:
            response = supabase.table("Vendor").select("Flags, FlagsAdded").eq("ID", vendor_id).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error in get_flags: {str(e)}")
            return None

    def get_state_link(self, state_name):
        """
        Fetches the Secretary of State link for a given state.
        """
        try:
            response = supabase.table("States").select("Link").eq("State", state_name).execute()
            if response.data:
                return response.data[0]["Link"]
            return None
        except Exception as e:
            print(f"Error fetching state link for {state_name}: {str(e)}")
            return None

    def get_vendor_by_id(self, vendor_id):
        """
        Fetches vendor information by vendor ID.
        """
        try:
            response = supabase.table("Vendor").select("*").eq("ID", vendor_id).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error in get_vendor_by_id: {str(e)}")
            return None


