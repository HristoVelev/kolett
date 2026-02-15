import datetime
import importlib
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from kolett.protocol import DeliveryInput, DeliveryOutput, ItemResult
from kolett.templating import render_manifest, render_path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kolett.engine")


class KolettEngine:
    def __init__(self, config: dict):
        self.config = config
        self.default_root = Path(
            config.get("storage", {}).get("root", "/tmp/kolett_deliveries")
        )
        self.template_dir = Path(
            config.get("paths", {}).get("template_dir", "templates")
        )

    def process_delivery(self, delivery: DeliveryInput) -> DeliveryOutput:
        """
        Executes the delivery process:
        1. Create delivery directory
        2. Copy/Rename items based on templates
        3. Generate Markdown manifest
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dest_root = (
            Path(delivery.destination_root)
            if delivery.destination_root
            else self.default_root
        )
        delivery_path = dest_root / delivery.package_name

        if delivery.dry_run:
            logger.info(
                f"DRY RUN: Starting delivery: {delivery.package_name} to {delivery_path}"
            )
        else:
            logger.info(
                f"Starting delivery: {delivery.package_name} to {delivery_path}"
            )

        results: List[ItemResult] = []

        # Ensure delivery directory exists
        if not delivery.dry_run:
            delivery_path.mkdir(parents=True, exist_ok=True)

        for item in delivery.items:
            try:
                # Render target filename
                target_filename = render_path(item.target_template, item.metadata)
                target_path = delivery_path / target_filename

                # Ensure subdirectories in target path exist (e.g. shots/s01/...)
                if not delivery.dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                source = Path(item.source_path)

                if not source.exists():
                    raise FileNotFoundError(
                        f"Source path does not exist: {item.source_path}"
                    )

                # Perform the copy
                if not delivery.dry_run:
                    # Note: For VFX sequences, we might want to extend this to handle directory copies/symlinks
                    if source.is_dir():
                        shutil.copytree(source, target_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source, target_path)

                results.append(
                    ItemResult(
                        source=str(source), destination=str(target_path), success=True
                    )
                )
                logger.info(f"Delivered: {source.name} -> {target_filename}")

            except Exception as e:
                logger.error(f"Failed to deliver {item.source_path}: {str(e)}")
                results.append(
                    ItemResult(
                        source=item.source_path,
                        destination="",
                        success=False,
                        error=str(e),
                    )
                )

        # Prepare context for manifest
        success_count = sum(1 for r in results if r.success)
        summary = (
            f"Successfully delivered {success_count} of {len(delivery.items)} items."
        )

        manifest_context = {
            "package_name": delivery.package_name,
            "timestamp": timestamp,
            "client_config": delivery.client_config,
            "delivery_path": str(delivery_path),
            "summary": summary,
            "results": results,
            "items": [
                {
                    "source": item.source_path,
                    "destination": render_path(item.target_template, item.metadata),
                    "metadata": item.metadata,
                    "error": next(
                        (
                            r.error
                            for r in results
                            if r.source == item.source_path and not r.success
                        ),
                        None,
                    ),
                }
                for item in delivery.items
            ],
        }

        # Render and write manifest
        manifest_content = render_manifest(
            "manifest.md.j2", str(self.template_dir), manifest_context
        )

        manifest_file = delivery_path / "manifest.md"
        if not delivery.dry_run:
            with open(manifest_file, "w") as f:
                f.write(manifest_content)
            logger.info(f"Manifest generated: {manifest_file}")
        else:
            logger.info(f"DRY RUN: Manifest would be generated at {manifest_file}")
            print("\n--- MANIFEST PREVIEW ---")
            print(manifest_content)
            print("--- END PREVIEW ---\n")

        output = DeliveryOutput(
            package_name=delivery.package_name,
            delivery_path=str(delivery_path),
            manifest_path=str(manifest_file),
            timestamp=timestamp,
            results=results,
            summary=summary,
        )

        # Execute Callbacks
        self._run_callbacks(delivery, output)

        return output

    def _run_callbacks(self, delivery: DeliveryInput, output: DeliveryOutput):
        """
        Dynamically loads and executes callback plugins defined in the input.
        """
        if not hasattr(delivery, "callbacks") or not delivery.callbacks:
            # Fallback to notifications list for backward compatibility if needed
            return

        for plugin_name, plugin_config in delivery.callbacks.items():
            try:
                logger.info(f"Executing callback plugin: {plugin_name}")

                # Dynamic import: kolett.plugins.output.{name}.plugin
                module_path = f"kolett.plugins.output.{plugin_name}.plugin"
                module = importlib.import_module(module_path)

                # Instantiate and run
                plugin_class = getattr(module, "Plugin")
                plugin_instance = plugin_class(plugin_config, dry_run=delivery.dry_run)
                plugin_instance.run(output)

            except Exception as e:
                logger.error(f"Callback plugin {plugin_name} failed: {str(e)}")
