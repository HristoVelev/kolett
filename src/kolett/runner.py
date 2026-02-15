import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

from kolett.engine import KolettEngine
from kolett.plugins.input.grist.plugin import GristConnector
from kolett.protocol import DeliveryInput

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("kolett.runner")


class KolettApp:
    def __init__(self, settings_path: str):
        self.settings_path = Path(settings_path)
        self.settings = self._load_settings()

        # Initialize Engine
        self.engine = KolettEngine(self.settings)

    def _load_settings(self) -> dict:
        """Loads the global YAML settings for the studio environment."""
        if not self.settings_path.exists():
            logger.error(f"Settings file not found: {self.settings_path}")
            sys.exit(1)

        with open(self.settings_path, "r") as f:
            settings = yaml.safe_load(f) or {}

        # Ensure template path is resolved relative to the runner
        if settings.get("paths") is None:
            settings["paths"] = {}
        if settings["paths"].get("template_dir") is None:
            project_root = Path(__file__).parent.parent.parent
            settings["paths"]["template_dir"] = str(project_root / "templates")

        return settings

    def run_by_package_id(self, package_id: str, dry_run: bool = False):
        """
        Main orchestration logic:
        1. Connect to Grist
        2. Find the Package by Package_ID
        3. Fetch associated Items
        4. Convert to Kolett Open Protocol
        5. Process via Engine
        """
        grist_cfg = self.settings.get("grist", {})
        api_key = grist_cfg.get("api_key")
        doc_id = grist_cfg.get("doc_id")
        server_url = grist_cfg.get("server_url", "https://grist.tail74e423.ts.net")

        if not api_key or not doc_id:
            logger.error("Grist api_key and doc_id must be defined in settings.yaml")
            sys.exit(1)

        connector = GristConnector(server_url, api_key, doc_id)

        # 1. Find the package record
        logger.info(f"Searching for package '{package_id}' in Grist...")
        packages = connector.fetch_delivery_data(
            "Packages", filter_dict={"Package_ID": [package_id]}
        )

        if not packages:
            logger.error(f"Package '{package_id}' not found in Grist.")
            sys.exit(1)

        package_record = packages[0]
        package_row_id = package_record["id"]

        # 2. Fetch all items linked to this package
        # Note: Grist stores Ref fields as row IDs
        logger.info(f"Fetching items for package row ID: {package_row_id}")
        items = connector.fetch_delivery_data(
            "Items", filter_dict={"Package": [package_row_id]}
        )

        if not items:
            logger.warning(f"No items found for package '{package_id}'.")

        # 3. Map to Kolett Protocol
        # We pass the global settings as the 'engine_config' for plugin resolution
        delivery_input = connector.map_to_kolett(
            package_record=package_record,
            item_records=items,
            client_config=package_record.get("fields", {}).get(
                "Client_Config", "standard"
            ),
            engine_config=self.settings,
        )

        if dry_run:
            delivery_input.dry_run = True

        # 4. Process Delivery
        logger.info(f"Handing off to Kolett Engine...")
        output = self.engine.process_delivery(delivery_input)

        logger.info("--- Delivery Complete ---")
        logger.info(f"Summary: {output.summary}")
        logger.info(f"Manifest: {output.manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Kolett Runner: Process VFX deliveries from Grist."
    )
    parser.add_argument(
        "package_id", help="The Package_ID from the Grist Packages table"
    )
    parser.add_argument(
        "--config", default="configs/settings.yaml", help="Path to global settings.yaml"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview delivery without file operations or callbacks",
    )

    args = parser.parse_args()

    app = KolettApp(args.config)
    app.run_by_package_id(args.package_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
