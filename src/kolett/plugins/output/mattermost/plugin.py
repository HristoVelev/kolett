import logging
from typing import Any, Dict

import requests

from kolett.plugins.base import CallbackPlugin
from kolett.protocol import DeliveryOutput

logger = logging.getLogger("kolett.plugins.output.mattermost")


class Plugin(CallbackPlugin):
    """
    Mattermost Callback Plugin for Kolett.
    Posts delivery status and manifest summaries to a Mattermost channel via Webhooks.
    """

    def run(self, delivery_output: DeliveryOutput) -> bool:
        webhook_url = self.config.get("webhook_url")
        channel = self.config.get("channel")
        username = self.config.get("username", "Kolett Delivery")
        icon_url = self.config.get(
            "icon_url", "https://grist.tail74e423.ts.net/icons/delivery.png"
        )

        if not webhook_url:
            logger.error("Mattermost webhook_url not provided in configuration.")
            return False

        if self.dry_run:
            logger.info(
                f"DRY RUN: Mattermost notification would be sent to channel '{channel}'"
            )
            return True

        # Build the message attachment
        status_color = (
            "#00FF00" if "Successfully" in delivery_output.summary else "#FF0000"
        )

        # Create a formatted message
        text = f"### 📦 Delivery Update: {delivery_output.package_name}\n"
        text += f"**Status:** {delivery_output.summary}\n"
        text += f"**Manifest:** [{delivery_output.manifest_path}](file://{delivery_output.manifest_path})\n"
        text += f"**Path:** `{delivery_output.delivery_path}`"

        payload = {
            "channel": channel,
            "username": username,
            "icon_url": icon_url,
            "text": text,
            "attachments": [
                {
                    "fallback": delivery_output.summary,
                    "color": status_color,
                    "fields": [
                        {
                            "short": True,
                            "title": "Package",
                            "value": delivery_output.package_name,
                        },
                        {
                            "short": True,
                            "title": "Timestamp",
                            "value": delivery_output.timestamp,
                        },
                    ],
                }
            ],
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(
                f"Mattermost notification sent for {delivery_output.package_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Mattermost notification: {str(e)}")
            return False
