import argparse
import importlib
import logging
import os
import sys
from pathlib import Path

import yaml

from kolett.engine import KolettEngine
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

        return settings

    def run_by_package_id(self, package_id: str, dry_run: bool = False):
        """
        Main orchestration logic:
        1. Load Active Input Plugin
        2. Fetch Delivery Data via Plugin
        3. Process via Engine
        """
        input_plugins = self.settings.get("plugins", {}).get("input", {})
        active_plugin_name = input_plugins.get("active")

        if not active_plugin_name:
            logger.error("No active input plugin defined in settings.yaml")
            sys.exit(1)

        plugin_config = input_plugins.get(active_plugin_name, {})

        try:
            # Dynamic import: kolett.plugins.input.{name}.plugin
            module_path = f"kolett.plugins.input.{active_plugin_name}.plugin"
            module = importlib.import_module(module_path)

            # Instantiate Input Plugin
            # Input plugins must expose an 'InputPlugin' class
            plugin_class = getattr(module, "InputPlugin")
            input_plugin = plugin_class(plugin_config, engine_config=self.settings)

            logger.info(
                f"Fetching package '{package_id}' via {active_plugin_name} plugin..."
            )
            delivery_input = input_plugin.fetch_package(package_id)

        except Exception as e:
            logger.error(
                f"Failed to load or execute input plugin '{active_plugin_name}': {e}"
            )
            sys.exit(1)

        if dry_run:
            delivery_input.dry_run = True

        # Process Delivery
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
