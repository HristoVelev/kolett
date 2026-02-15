import logging
import os
from typing import Any, Dict, List, Optional

import requests

from kolett.protocol import DeliveryInput, PackageItem

logger = logging.getLogger("kolett.plugins.input.grist")


class GristConnector:
    """
    Connector for Grist (https://getgrist.com/).
    Fetches rows from a specified table and converts them into Kolett Open Protocol JSON.
    """

    def __init__(self, server_url: str, api_key: str, doc_id: str):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.doc_id = doc_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def fetch_delivery_data(
        self, table_id: str, filter_dict: Optional[Dict[str, List[Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches raw rows from a Grist table.
        """
        endpoint = f"{self.server_url}/api/docs/{self.doc_id}/tables/{table_id}/records"

        params = {}
        if filter_dict:
            import json

            params["filter"] = json.dumps(filter_dict)

        response = requests.get(endpoint, headers=self.headers, params=params)
        response.raise_for_status()

        return response.json().get("records", [])

    def map_to_kolett(
        self,
        package_record: Dict[str, Any],
        item_records: List[Dict[str, Any]],
        client_config: str,
        engine_config: Dict[str, Any] = None,
    ) -> DeliveryInput:
        """
        Maps Grist Package and Item records to Kolett DeliveryInput.
        """
        package_fields = package_record.get("fields", {})
        package_name = package_fields.get("Package_ID", "Unknown_Package")

        items = []
        for record in item_records:
            fields = record.get("fields", {})

            source = fields.get("Folder_Internal")
            template = fields.get("Target_Template")

            if not source or not template:
                logger.warning(
                    f"Skipping item {record.get('id')} due to missing Folder_Internal or Target_Template."
                )
                continue

            # Extract metadata from item and package fields
            metadata = {k: str(v) for k, v in fields.items() if v is not None}
            # Add package-level metadata to items
            for k, v in package_fields.items():
                if v is not None and k not in metadata:
                    metadata[f"pkg_{k}"] = str(v)

            items.append(
                PackageItem(
                    source_path=source, target_template=template, metadata=metadata
                )
            )

        # Build callbacks from engine_config
        callbacks = {}
        if engine_config and "plugins" in engine_config:
            callbacks = engine_config["plugins"].get("callbacks", {})

            # Inject Grist specific data into grist_update callback if present
            if "grist_update" in callbacks:
                callbacks["grist_update"]["doc_id"] = self.doc_id
                callbacks["grist_update"]["record_id"] = package_record.get("id")
                callbacks["grist_update"]["api_key"] = self.api_key

        return DeliveryInput(
            package_name=package_name,
            client_config=client_config,
            items=items,
            callbacks=callbacks,
        )

    def update_delivery_status(
        self, table_id: str, record_id: int, status_data: Dict[str, Any]
    ):
        """
        Updates a row in Grist with the result of the delivery.
        """
        endpoint = f"{self.server_url}/api/docs/{self.doc_id}/tables/{table_id}/records"

        payload = {"records": [{"id": record_id, "fields": status_data}]}

        response = requests.patch(endpoint, headers=self.headers, json=payload)
        response.raise_for_status()
        logger.info(f"Updated Grist record {record_id} with status: {status_data}")


def main():
    """
    Example CLI usage for the connector.
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Kolett Grist Connector")
    parser.add_argument("--server", required=True, help="Grist Server URL")
    parser.add_argument("--api-key", required=True, help="Grist API Key")
    parser.add_argument("--doc", required=True, help="Grist Document ID")
    parser.add_argument("--table", required=True, help="Grist Table ID")
    parser.add_argument("--package", required=True, help="Package Name")
    parser.add_argument("--client", default="default", help="Client Config Name")
    parser.add_argument(
        "--filter", help='JSON filter for rows (e.g. \'{"Status": ["Ready"]}\')'
    )

    args = parser.parse_args()

    connector = GristConnector(args.server, args.api_key, args.doc)

    filters = json.loads(args.filter) if args.filter else None
    records = connector.fetch_delivery_data(args.table, filters)

    delivery_input = connector.map_to_kolett(records, args.package, args.client)

    # Output the Open Protocol JSON to stdout for the Kolett Engine
    print(delivery_input.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
