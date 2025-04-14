from datetime import date
from supabase import create_client, Client
from sqlalchemy.dialects.postgresql import ARRAY
import os
import flask
from flask import Flask, request, jsonify
from dotenv import load_dotenv


# Initialize Supabase client
load_dotenv()
PROJECTURL = os.getenv("projecturl")
ANONKEY = os.getenv("anonkey")
supabase: Client = create_client(PROJECTURL, ANONKEY)

class DatabaseDriver:
    """
    Database driver for interacting with Supabase.
    Handles reading and writing information with the Supabase database.
    """
    
    def __init__(self):
        self.supabase = create_client(PROJECTURL, ANONKEY)
        print(f"Supabase client initialized with URL: {PROJECTURL}")

    def get_account_by_id(self, account_id=None):
        """
        Fetches account information by account ID from Supabase.
        """
        try:
            response = self.supabase.table("Account").select("*").eq("ID", account_id).execute()
            print(f"Response: {response}")
                
            if not response.data:
                return None
                
            account = response.data[0]
            
            try:
                equipment_response = self.supabase.table("Equipment").select("*").eq("AccountID", account_id).execute()
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
        response = self.supabase.table("Equipment").select("*").eq("AccountID", account_id).execute()
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
                "Account.Name": account["Name"],
                "Account.Address": f"{account['Street']}, {account['City']}, {account['State']}, {account['ZIP']}",
                "Vendor.Name": vendor["Name"],
                "Vendor.Address": f"{vendor['Street']}, {vendor['City']}, {vendor['State']}, {vendor['ZIP']}",
                "Vendor.Website": vendor["Website"]    
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
            vendor_response = self.supabase.table("Vendor").select("*").eq("ID", vendor_id).execute()
            if not vendor_response.data:
                return False

            vendor = vendor_response.data[0]
            flags_added = vendor.get("Flags", [])
            flags_added.append(flag)

            # Update the vendor
            update_response = self.supabase.table("Vendor").update({
                "Flags": flags_added,
                "NumFlags": vendor.get("NumFlags", 0) + 1,
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
            response = self.supabase.table("Vendor").select("NumFlags, Flags").eq("ID", vendor_id).execute()
            
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
            response = self.supabase.table("States").select("Link").eq("State", state_name).execute()
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
            response = self.supabase.table("Vendor").select("*").eq("ID", vendor_id).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error in get_vendor_by_id: {str(e)}")
            return None
        
    def get_vendor_by_name(self, vendor_name):
        """
        Fetches vendor information by vendor name.
        """
        response = self.supabase.table("Vendor").select("*").eq("Name", vendor_name).execute()
        return response.data[0] if response.data else None
    
    def update_sos_info(self, vendor_id, years, active): 
        """
        Updates Vendor.SosYearsInBusiness (float) and Vendor.SosActive (boolean)
        """
        try:    
            response = self.supabase.table("Vendor").update({
                "SosYearsInBusiness": years,
                "SosActive": active
            }).eq("ID", vendor_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating sos info: {str(e)}")

    def update_ofac_info(self, vendor_id, hit_found):
        """Updates Vendor.OfacHitFound (boolean)"""
        try:
            response = self.supabase.table("Vendor").update({
                "OfacHitFound": hit_found
            }).eq("ID", vendor_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating ofac info: {str(e)}")

    def get_accounts(self):
        """Returns all accounts (sample data)"""
        response = self.supabase.table("Account").select("*").execute()
        return response.data if response.data else []
    
    def get_vendors(self):  
        """Returns all vendors (sample data)"""
        response = self.supabase.table("Vendor").select("*").execute()
        return response.data if response.data else []
            