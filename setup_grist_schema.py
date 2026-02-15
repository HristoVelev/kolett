import json
import sys

import requests

# Grist Configuration
GRIST_SERVER = "https://grist.tail74e423.ts.net"
API_KEY = "d27435bf2be63170c71432b073c18ccba54e9e5c"
DOC_ID = "n4hcbNVbWVELK17zwK2pNX"

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def create_tables():
    """
    Creates the Users, Items, and Packages tables in Grist.
    """
    endpoint = f"{GRIST_SERVER}/api/docs/{DOC_ID}/tables"

    # We define the tables according to the schema notes
    tables_payload = {
        "tables": [
            {
                "id": "Users",
                "columns": [
                    {"id": "Name", "type": "Text"},
                    {"id": "Email", "type": "Text"},
                    {"id": "Org", "type": "Text"},
                    {"id": "Handle", "type": "Text"},
                ],
            },
            {
                "id": "Packages",
                "columns": [
                    {"id": "Date", "type": "Date"},
                    {
                        "id": "Status",
                        "type": "Choice",
                        "widgetOptions": json.dumps(
                            {
                                "choices": [
                                    "Draft",
                                    "Ready",
                                    "Processing",
                                    "Delivered",
                                    "Failed",
                                ]
                            }
                        ),
                    },
                    {"id": "Number", "type": "Text"},
                    {"id": "Package_ID", "type": "Text"},
                    {"id": "Description", "type": "Text"},
                    {"id": "Path_to_Delivery_Folder", "type": "Text"},
                    # Reference to Users (Many-to-Many via RefList)
                    {"id": "Notification_Users", "type": "RefList:Users"},
                ],
            },
            {
                "id": "Items",
                "columns": [
                    {"id": "Item_ID", "type": "Text"},
                    {"id": "Folder_Internal", "type": "Text"},
                    {"id": "Folder_Delivery", "type": "Text"},
                    {"id": "Description", "type": "Text"},
                    {"id": "Target_Template", "type": "Text"},
                    # Link to Packages (Many-to-One)
                    {"id": "Package", "type": "Ref:Packages"},
                ],
            },
        ]
    }

    print(f"Creating tables in document {DOC_ID}...")
    response = requests.post(endpoint, headers=HEADERS, json=tables_payload)

    if response.status_code == 200:
        print("Successfully created tables.")
    else:
        print(f"Error creating tables: {response.status_code}")
        print(response.text)
        sys.exit(1)


def add_sample_data():
    """
    Adds some initial sample data to get started.
    """
    # 1. Add a User
    user_endpoint = f"{GRIST_SERVER}/api/docs/{DOC_ID}/tables/Users/records"
    user_data = {
        "records": [
            {
                "fields": {
                    "Name": "Hristo Velev",
                    "Email": "hristo@bottleshipvfx.com",
                    "Org": "BTL",
                    "Handle": "hristo",
                }
            }
        ]
    }
    requests.post(user_endpoint, headers=HEADERS, json=user_data)

    # 2. Add a Package
    pkg_endpoint = f"{GRIST_SERVER}/api/docs/{DOC_ID}/tables/Packages/records"
    pkg_data = {
        "records": [
            {
                "fields": {
                    "Package_ID": "BTL_EP01_DEL_v01",
                    "Status": "Draft",
                    "Description": "First test delivery via Kolett",
                    "Number": "001",
                }
            }
        ]
    }
    pkg_res = requests.post(pkg_endpoint, headers=HEADERS, json=pkg_data).json()
    pkg_row_id = pkg_res["records"][0]["id"]

    # 3. Add Items linked to that Package
    item_endpoint = f"{GRIST_SERVER}/api/docs/{DOC_ID}/tables/Items/records"
    item_data = {
        "records": [
            {
                "fields": {
                    "Item_ID": "sh010",
                    "Folder_Internal": "/mnt/prod/projects/test/sh010/render",
                    "Target_Template": "{{ shot_code }}_{{ version }}.exr",
                    "Package": pkg_row_id,
                }
            }
        ]
    }
    requests.post(item_endpoint, headers=HEADERS, json=item_data)
    print("Sample data added.")


if __name__ == "__main__":
    create_tables()
    add_sample_data()
    print(f"\nSchema setup complete! Access your doc at: {GRIST_SERVER}/doc/{DOC_ID}")
