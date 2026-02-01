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

update_referral_date("djienfjen", '2026-2-12')