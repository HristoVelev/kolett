import argparse
import json
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
logger = logging.getLogger("kolett.cli")


def load_config(config_path: str) -> dict:
    """Loads the YAML configuration file."""
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        return {}

    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(
        description="Kolett: An open-source delivery tool for VFX packages."
    )

    parser.add_argument(
        "input", help="Path to the delivery input JSON file (Open Protocol)"
    )

    parser.add_argument(
        "--config",
        default="configs/settings.yaml",
        help="Path to the Kolett settings YAML file",
    )

    parser.add_argument(
        "--output", help="Path to write the result JSON (Delivery Output)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview delivery without moving files or triggering callbacks",
    )

    args = parser.parse_args()

    # 1. Load Global Config
    config = load_config(args.config)

    # Ensure template dir is absolute or relative to execution
    if config.get("paths") is None:
        config["paths"] = {}

    if config["paths"].get("template_dir") is None:
        # Default to the 'templates' directory relative to the project root
        project_root = Path(__file__).parent.parent.parent
        config["paths"]["template_dir"] = str(project_root / "templates")

    # 2. Parse Input JSON
    try:
        with open(args.input, "r") as f:
            input_data = json.load(f)
            delivery_input = DeliveryInput(**input_data)

            # Override dry_run if CLI flag provided
            if args.dry_run:
                delivery_input.dry_run = True
    except Exception as e:
        logger.error(f"Failed to parse input JSON: {e}")
        sys.exit(1)

    # 3. Initialize Engine
    engine = KolettEngine(config)

    # 4. Run Delivery
    try:
        output_result = engine.process_delivery(delivery_input)

        # 5. Emit Result JSON
        result_json = output_result.model_dump_json(indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(result_json)
            logger.info(f"Result JSON written to {args.output}")
        else:
            # Print to stdout if no output path provided
            print(result_json)

    except Exception as e:
        logger.error(f"Engine failed to process delivery: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
