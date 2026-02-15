import logging
from typing import Any, Dict

import requests

from kolett.plugins.base import CallbackPlugin
from kolett.protocol import DeliveryOutput

logger = logging.getLogger("kolett.plugins.output.grist_update")


class Plugin(CallbackPlugin):
    """
    Grist Update Callback Plugin for Kolett.
    Updates the status and delivery path of a package in Grist after the engine finishes.
    """

    def run(self, delivery_output: DeliveryOutput) -> bool:
        server_url = self.config.get("server_url", "https://grist.tail74e423.ts.net")
        api_key = self.config.get("api_key")
        doc_id = self.config.get("doc_id")
        table_id = self.config.get("table_id", "Packages")
        record_id = self.config.get("record_id")

        if not api_key or not doc_id or not record_id:
            logger.error(
                "Missing Grist configuration: api_key, doc_id, and record_id are required."
            )
            return False

        if self.dry_run:
            logger.info(
                f"DRY RUN: Grist record {record_id} in table '{table_id}' would be updated "
                f"with status 'Delivered' and path '{delivery_output.delivery_path}'"
            )
            return True

        endpoint = (
            f"{server_url.rstrip('/')}/api/docs/{doc_id}/tables/{table_id}/records"
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Determine status based on summary
        status = "Delivered" if "Successfully" in delivery_output.summary else "Failed"

        payload = {
            "records": [
                {
                    "id": int(record_id),
                    "fields": {
                        "Status": status,
                        "Path_to_Delivery_Folder": delivery_output.delivery_path,
                        "Description": delivery_output.summary,
                    },
                }
            ]
        }

        try:
            response = requests.patch(
                endpoint, headers=headers, json=payload, timeout=10
            )
            response.raise_for_status()
            logger.info(
                f"Successfully updated Grist record {record_id} status to {status}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update Grist: {str(e)}")
            return False
