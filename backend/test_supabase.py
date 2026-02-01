import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")  # or SUPABASE_SERVICE_ROLE_KEY

print(f"Testing connection to: {url}")

try:
    supabase = create_client(url, key)
    # Try listing tables (will work if connection is successful)
    print("✅ Connection successful!")
    print(f"Supabase client created and authenticated")
    
    # Try a simple query on a table that should exist
    try:
        response = supabase.table("users").select("*").limit(1).execute()
        print(f"✅ Successfully queried 'users' table")
        print(f"Result: {response}")
    except Exception as e:
        print(f"Note: Could not query 'users' table (it may not exist yet): {e}")
        print("This is normal if you haven't run the schema.sql yet")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")