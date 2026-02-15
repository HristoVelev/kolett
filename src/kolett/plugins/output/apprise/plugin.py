import logging
from typing import Any, Dict

import requests

from kolett.plugins.base import CallbackPlugin
from kolett.protocol import DeliveryOutput

logger = logging.getLogger("kolett.plugins.output.apprise")


class Plugin(CallbackPlugin):
    """
    Apprise Output Plugin for Kolett.
    Sends notifications via a self-hosted Apprise API instance or Apprise library.
    Since the studio already has an Apprise service on APS (10.1.30.x / 100.79.23.17),
    this plugin defaults to the API approach.
    """

    def run(self, delivery_output: DeliveryOutput) -> bool:
        apprise_url = self.config.get("api_url")  # e.g., http://10.1.30.17:8085/notify
        targets = self.config.get(
            "targets", []
        )  # List of apprise URLs (e.g. mmost://...)
        tags = self.config.get(
            "tags", []
        )  # Tags to filter if using global apprise config

        if not apprise_url:
            logger.error("Apprise 'api_url' not provided in configuration.")
            return False

        if not targets and not tags:
            logger.warning("Neither 'targets' nor 'tags' provided for Apprise plugin.")

        if self.dry_run:
            logger.info(
                f"DRY RUN: Apprise notification would be sent to {apprise_url} "
                f"with targets: {targets} and tags: {tags}"
            )
            return True

        # Build notification body
        title = f"Kolett Delivery: {delivery_output.package_name}"
        body = f"**Status:** {delivery_output.summary}\n"
        body += f"**Timestamp:** {delivery_output.timestamp}\n"
        body += f"**Delivery Path:** `{delivery_output.delivery_path}`\n\n"
        body += f"Detailed manifest available at: {delivery_output.manifest_path}"

        payload = {
            "title": title,
            "body": body,
            "type": "info" if "Successfully" in delivery_output.summary else "failure",
            "format": "markdown",
        }

        if targets:
            payload["urls"] = ",".join(targets)
        if tags:
            payload["tags"] = ",".join(tags)

        try:
            response = requests.post(apprise_url, json=payload, timeout=15)
            response.raise_for_status()
            logger.info(
                f"Apprise notification successfully sent for {delivery_output.package_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Apprise notification: {str(e)}")
            return False
