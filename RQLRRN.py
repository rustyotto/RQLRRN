import requests
import json
import os
import csv

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

# --- Function to Perform RQL Config Search ---
def search_asset_by_rql(rql_query):
    """
    Performs a config search using the provided RQL query and returns the results.
    """
    if not TOKEN:
        print("Authentication token not found. Please login first.")
        return None

    headers = {
        "x-redlock-auth": TOKEN,
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json; charset=UTF-8"
    }
    search_url = f"{PRISMA_CLOUD_API_URL}/search/config"
    
    # The Search API requires a timeRange object in the payload.
    # 'to_now' with 'epoch' searches all historical data.
    payload = {
        "query": rql_query,
        "timeRange": {
            "type": "to_now",
            "value": "epoch"
        },
        "limit": 10 # Limit the number of results, adjust as needed
    }
    
    print(f"\nExecuting RQL search...")
    print(f"Endpoint: {search_url}")
    print(f"Query: {rql_query}")

    try:
        response = requests.post(search_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error during search: {errh}")
        response_text = errh.response.text if errh.response else "No response body"
        print(f"Response body: {response_text}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred during search: {err}")
    
    return None

# --- Main Script Execution ---
def main():
    """Main function to orchestrate the script."""
    # Configuration Check
    if "YOUR_ACCESS_KEY_ID" in ACCESS_KEY or "YOUR_SECRET_KEY" in SECRET_KEY:
        print("ERROR: Please update ACCESS_KEY and SECRET_KEY with your actual details or set environment variables.")
        return

    if login_to_prisma_cloud():
        # Define the RQL query to find a specific EC2 instance by its ID.
        instance_id_to_find = "i-03a2bae0e2e2f1c13"
        rql_query = f"config from cloud.resource where api.name = 'aws-ec2-describe-instances' AND json.rule = instanceId equals \"{instance_id_to_find}\""
        
        search_results = search_asset_by_rql(rql_query)
        
        # The actual list of assets is nested inside search_results['data']['items']
        asset_list = []
        if search_results and isinstance(search_results.get('data'), dict):
            asset_list = search_results['data'].get('items', [])
        elif search_results and isinstance(search_results.get('data'), list):
            # Fallback for the originally expected format
            asset_list = search_results['data']

        if asset_list:
            print(f"\n--- Found {len(asset_list)} asset(s) ---")
            
            # Prepare data for CSV
            csv_data = []
            for asset_item in asset_list:
                asset = {} # Initialize asset as a dictionary
                # Check if the item from the API is a string; if so, try to parse it as JSON.
                if isinstance(asset_item, str):
                    try:
                        asset = json.loads(asset_item)
                    except json.JSONDecodeError:
                        print(f"  Warning: Found a string in the data list that is not valid JSON, skipping: {asset_item[:100]}...")
                        continue # Skip this item
                elif isinstance(asset_item, dict):
                    # This is the expected case where the item is already a dictionary
                    asset = asset_item
                else:
                    print(f"  Warning: Found an unexpected data type in the results list, skipping: {type(asset_item)}")
                    continue # Skip this item

                # The actual resource details are often in a nested 'data' field
                resource_details = asset.get('data', {})
                
                # Extract the 'Name' tag from the tags list
                instance_name = "N/A"
                if 'tags' in resource_details and isinstance(resource_details['tags'], list):
                    for tag in resource_details['tags']:
                        if tag.get('key') == 'Name':
                            instance_name = tag.get('value')
                            break
                
                # Flatten the data for the CSV row
                row = {
                    "AssetID": asset.get('unifiedAssetId') or asset.get('rrn', 'N/A'),
                    "InstanceID": resource_details.get('instanceId', 'N/A'),
                    "InstanceName": instance_name,
                    "InstanceType": resource_details.get('instanceType', 'N/A'),
                    "State": resource_details.get('state', {}).get('name', 'N/A'),
                    "PrivateIP": resource_details.get('privateIpAddress', 'N/A'),
                    "PublicIP": resource_details.get('publicIpAddress', 'N/A'),
                    "VPC_ID": resource_details.get('vpcId', 'N/A'),
                    "SubnetID": resource_details.get('subnetId', 'N/A'),
                    "Region": asset.get('region', 'N/A'),
                    "AccountID": asset.get('accountId', 'N/A')
                }
                csv_data.append(row)
            
            # Write data to CSV file
            output_filename = "asset_report.csv"
            if csv_data:
                try:
                    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
                        # The header is derived from the keys of the first dictionary
                        header = csv_data[0].keys()
                        writer = csv.DictWriter(csvfile, fieldnames=header)
                        writer.writeheader()
                        writer.writerows(csv_data)
                    print(f"\nSuccessfully wrote asset information to {output_filename}")
                except IOError as e:
                    print(f"\nError writing to CSV file: {e}")

        else:
            print(f"\nSearch failed or no assets found matching the instance ID: {instance_id_to_find}")

if __name__ == "__main__":
    main()
