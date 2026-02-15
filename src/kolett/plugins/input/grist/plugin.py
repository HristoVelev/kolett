import logging
from typing import Any, Dict, List, Optional

import requests

from kolett.protocol import DeliveryInput, PackageItem

logger = logging.getLogger("kolett.plugins.input.grist")


class InputPlugin:
    """
    Grist Input Plugin for Kolett.
    Fetches package and item data from a Grist document and translates it
    to the Kolett Open Protocol.
    """

    def __init__(self, config: Dict[str, Any], engine_config: Dict[str, Any] = None):
        """
        Initializes the plugin with its specific config and the global engine settings.
        """
        self.server_url = config.get(
            "server_url", "https://grist.tail74e423.ts.net"
        ).rstrip("/")
        self.api_key = config.get("api_key")
        self.doc_id = config.get("doc_id")
        self.engine_config = engine_config or {}

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def fetch_package(self, package_id: str) -> DeliveryInput:
        """
        Main entry point for the input plugin.
        Resolves a package ID into a full DeliveryInput object.
        """
        # 1. Fetch Package Record
        packages = self._get_records(
            "Packages", filter_dict={"Package_ID": [package_id]}
        )
        if not packages:
            raise ValueError(f"Package '{package_id}' not found in Grist.")

        package_record = packages[0]
        package_row_id = package_record["id"]
        package_fields = package_record.get("fields", {})

        # 2. Fetch Linked Items from RefList
        item_ids = package_fields.get("Items", [])
        # Grist RefList format is ["L", id1, id2, ...]
        if isinstance(item_ids, list) and len(item_ids) > 1 and item_ids[0] == "L":
            item_ids = item_ids[1:]
        elif not isinstance(item_ids, list):
            item_ids = []

        items = []
        if item_ids:
            items = self._get_records("Items", filter_dict={"id": item_ids})

        # 3. Map to Protocol
        return self._map_to_protocol(package_record, items)

    def _get_records(
        self, table_id: str, filter_dict: Optional[Dict[str, List[Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Internal helper to fetch records from Grist API."""
        endpoint = f"{self.server_url}/api/docs/{self.doc_id}/tables/{table_id}/records"
        params = {}
        if filter_dict:
            import json

            params["filter"] = json.dumps(filter_dict)

        response = requests.get(endpoint, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("records", [])

    def _map_to_protocol(
        self, package_record: Dict[str, Any], item_records: List[Dict[str, Any]]
    ) -> DeliveryInput:
        """Maps Grist specific records to the standard Kolett DeliveryInput."""
        package_fields = package_record.get("fields", {})

        # Determine the human-friendly folder name
        package_name = (
            package_fields.get("Package_Name")
            or package_fields.get("Name")
            or package_fields.get("Package_ID")
            or f"Package_{package_record.get('id')}"
        )

        items = []
        for record in item_records:
            fields = record.get("fields", {})
            source = fields.get("Folder_Internal")
            template = fields.get("Target_Template")

            if not source or not template:
                continue

            # Metadata aggregation (Item fields + prefixed Package fields)
            metadata = {k: str(v) for k, v in fields.items() if v is not None}

            # Map flexible Grist ID fields to standard metadata for templating
            if "Item_ID" in fields:
                metadata["item_id"] = str(fields["Item_ID"])
            if "Name" in fields:
                metadata["item_name"] = str(fields["Name"])
            for k, v in package_fields.items():
                if v is not None and k not in metadata:
                    metadata[f"pkg_{k}"] = str(v)

            items.append(
                PackageItem(
                    source_path=source,
                    target_template=template,
                    process_method=fields.get("Process_Method", "copy"),
                    metadata=metadata,
                )
            )

        # Build callbacks from global engine config
        callbacks = {}
        output_config = self.engine_config.get("plugins", {}).get("output", {})

        for plugin_name, plugin_settings in output_config.items():
            # Clone settings to avoid mutating global config
            cb_config = plugin_settings.copy()

            # Context injection for grist_update
            if plugin_name == "grist_update":
                cb_config["api_key"] = self.api_key
                cb_config["doc_id"] = self.doc_id
                cb_config["record_id"] = package_record.get("id")
                cb_config["server_url"] = self.server_url

            callbacks[plugin_name] = cb_config

        return DeliveryInput(
            package_name=package_name,
            client_config=package_fields.get("Client_Config", "standard"),
            items=items,
            callbacks=callbacks,
        )
