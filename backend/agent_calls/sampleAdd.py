from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

def update_referral_date(patient_name, new_referral_date):
    """
    Update the referral date for a patient by name.

    Args:
        patient_name: The name of the patient to update
        new_referral_date: The new referral date in format 'YYYY-MM-DD'

    Returns:
        dict: Response data with updated record(s) or error message
    """
    try:
        # Update the referral_date for matching patient_name
        response = supabase.table("referrals").update({
            "referral_date": new_referral_date
        }).eq("patient_name", patient_name).execute()

        if response.data and len(response.data) > 0:
            print(f"Successfully updated referral date for {patient_name} to {new_referral_date}")
            print(f"Updated {len(response.data)} record(s)")
            return {"success": True, "data": response.data}
        else:
            print(f"No records found for patient name: {patient_name}")
            return {"success": False, "message": "No matching records found"}

    except Exception as e:
        print(f"Error updating referral date: {e}")
        return {"success": False, "error": str(e)}

def update_scheduled_date(patient_name, new_scheduled_date):
    """
    Update the scheduled date for a patient by name.

    Args:
        patient_name: The name of the patient to update
        new_scheduled_date: The new scheduled date in format 'YYYY-MM-DD'

    Returns:
        dict: Response data with updated record(s) or error message
    """
    try:
        # Update the referral_date for matching patient_name
        response = supabase.table("referrals").update({
            "scheduled_date": new_scheduled_date
        }).eq("patient_name", patient_name).execute()

        if response.data and len(response.data) > 0:
            print(f"Successfully updated scheduled date for {patient_name} to {new_scheduled_date}")
            print(f"Updated {len(response.data)} record(s)")
            return {"success": True, "data": response.data}
        else:
            print(f"No records found for patient name: {patient_name}")
            return {"success": False, "message": "No matching records found"}

    except Exception as e:
        print(f"Error updating scheduled date: {e}")
        return {"success": False, "error": str(e)}
    
# update_scheduled_date("Parth Joshi", "2026-06-07 09:00:00+00")


def get_scheduled_dates(specialist_type):
    """
    Get all scheduled dates for a patient by name.

    Args:
        patient_name: The name of the patient to search for

    Returns:
        dict: Response data with list of scheduled dates or error message
    """
    try:
        # Query all referrals matching patient_name and select scheduled_date
        response = supabase.table("referrals").select(
            "id, scheduled_date, status"
        ).eq("specialist_type", specialist_type.upper()).execute()

        if response.data and len(response.data) > 0:
            # Extract just the scheduled_date values (filter out None values)
            scheduled_dates = [
                record["scheduled_date"] 
                for record in response.data 
                if record["scheduled_date"] is not None
            ]
            
            print(f"Found {len(response.data)} record(s) for {specialist_type}")
            print(f"Scheduled dates: {specialist_type}")
            
            return scheduled_dates
        
        else:
            print(f"No records found for specialist type: {specialist_type}")
            return False

    except Exception as e:
        print(f"Error retrieving scheduled dates: {e}")
        return {"success": False, "error": str(e)}
    



# Example usage:
result = get_scheduled_dates("Cardiology")

print(result)