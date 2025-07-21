import requests
import json
import os

# --- Configuration ---
# It's recommended to use environment variables for credentials.
# Example: export PRISMA_ACCESS_KEY="your_access_key"
#          export PRISMA_SECRET_KEY="your_secret_key"
PRISMA_CLOUD_API_URL = "https://api.prismacloud.io"
ACCESS_KEY = os.getenv("PRISMA_ACCESS_KEY", "YOUR_ACCESS_KEY_ID") # Replace with your Access Key ID if not using env vars
SECRET_KEY = os.getenv("PRISMA_SECRET_KEY", "YOUR_SECRET_KEY")    # Replace with your Secret Key if not using env vars

TOKEN = ""

# --- Function to handle API Login ---
def login_to_prisma_cloud():
    """Logs into Prisma Cloud and stores the auth token globally."""
    global TOKEN
    payload = {"username": ACCESS_KEY, "password": SECRET_KEY}
    headers = {"Content-Type": "application/json", "Accept": "application/json; charset=UTF-8"}
    login_url = f"{PRISMA_CLOUD_API_URL}/login"
    print(f"Attempting login to: {login_url}...")
    try:
        response = requests.post(login_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        TOKEN = response.json().get("token")
        if TOKEN:
            print("Login successful.")
            return True
        else:
            print("Login successful, but no token was received.")
            return False
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error during login: {errh}")
        response_text = errh.response.text if errh.response else "No response body"
        print(f"Response body: {response_text}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred during login: {err}")
    return False

# --- Function to Get Asset Details by ID ---
def get_asset_details(asset_id):
    """
    Fetches detailed information for a specific asset using its ID (RRN or UAI).
    """
    if not TOKEN:
        print("Authentication token not found. Please login first.")
        return None

    headers = {
        "x-redlock-auth": TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    details_url = f"{PRISMA_CLOUD_API_URL}/uai/v1/asset"
    
    # The payload requires the assetId and the type of information to retrieve.
    # 'asset' is used to get the general, raw configuration details.
    payload = {
      "assetId": asset_id,
      "type": "asset"
    }
    
    print(f"\nFetching details for asset: {asset_id}")
    print(f"Endpoint: {details_url}")

    try:
        response = requests.post(details_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error fetching asset details: {errh}")
        response_text = errh.response.text if errh.response else "No response body"
        print(f"Response body: {response_text}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred fetching asset details: {err}")
    
    return None

# --- Main Script Execution ---
def main():
    """Main function to orchestrate the script."""
    # Configuration Check
    if "YOUR_ACCESS_KEY_ID" in ACCESS_KEY or "YOUR_SECRET_KEY" in SECRET_KEY:
        print("ERROR: Please update ACCESS_KEY and SECRET_KEY with your actual details or set environment variables.")
        return

    if login_to_prisma_cloud():
        # The specific RRN you provided for the EC2 instance
        asset_rrn_to_find = "rrn::instance:eu-west-3:xxxx0:xxxxx0:i-000xxxxx"
        
        asset_details = get_asset_details(asset_rrn_to_find)
        
        if asset_details:
            print("\n--- Asset Details Response Received ---")
            
            # --- MODIFIED TO OUTPUT TO FILE ---
            # Create a filename based on the instance ID from the RRN
            instance_id = asset_rrn_to_find.split(':')[-1]
            output_filename = f"asset_details_{instance_id}.txt"
            
            print(f"Writing full asset details to file: {output_filename}")
            
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    # Write the pretty-printed JSON to the file
                    f.write(json.dumps(asset_details, indent=4))
                print(f"Successfully wrote details to {output_filename}")
            except IOError as e:
                print(f"Error writing to file: {e}")

        else:
            print(f"\nFailed to retrieve details for asset: {asset_rrn_to_find}")

if __name__ == "__main__":
    main()
