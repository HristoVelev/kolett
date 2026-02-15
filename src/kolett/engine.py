import datetime
import importlib
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from kolett.protocol import DeliveryInput, DeliveryOutput, ItemResult
from kolett.templating import render_path

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
                source = Path(item.source_path)
                if not source.exists():
                    raise FileNotFoundError(
                        f"Source path does not exist: {item.source_path}"
                    )

                # Collect files to process (single file or directory contents)
                sources_to_copy = []
                if source.is_dir():
                    # Collect all files recursively, but we might want to preserve
                    # relative structure or flatten depending on target_template logic.
                    # For now, we collect top-level files to match common VFX sequence/folder patterns.
                    sources_to_copy = [f for f in source.iterdir() if f.is_file()]
                    if not sources_to_copy:
                        logger.warning(f"Source directory is empty: {source}")
                else:
                    sources_to_copy = [source]

                for src_file in sources_to_copy:
                    # Enrich metadata with file-specific info
                    file_metadata = item.metadata.copy()
                    file_metadata.update(
                        {
                            "src_name": src_file.name,
                            "src_base": src_file.stem,
                            "src_ext": src_file.suffix.lstrip("."),
                        }
                    )

                    # Render target path if template is provided, otherwise use original name
                    if item.target_template:
                        try:
                            target_filename = render_path(
                                item.target_template, file_metadata
                            )
                        except Exception as template_err:
                            logger.warning(
                                f"Template rendering failed for {src_file.name}: {template_err}. Falling back to original name."
                            )
                            target_filename = src_file.name
                    else:
                        target_filename = src_file.name

                    target_path = delivery_path / target_filename

                    # Ensure subdirectories in target path exist
                    if not delivery.dry_run:
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Perform the process via plugin
                    success = self._run_process_plugin(
                        item.process_method,
                        str(src_file),
                        str(target_path),
                        file_metadata,
                        delivery.dry_run,
                    )

                    results.append(
                        ItemResult(
                            source=str(src_file),
                            destination=str(target_path),
                            description=item.metadata.get("description")
                            or item.metadata.get("Description"),
                            success=success,
                        )
                    )
                    if success:
                        logger.info(f"Delivered: {src_file.name} -> {target_filename}")

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

        # Prepare summary
        success_count = sum(1 for r in results if r.success)
        summary = f"Successfully delivered {success_count} files across {len(delivery.items)} items."

        output = DeliveryOutput(
            package_name=delivery.package_name,
            delivery_path=str(delivery_path),
            manifest_path=str(delivery_path / "manifest.md"),
            timestamp=timestamp,
            results=results,
            summary=summary,
        )

        # Execute Callbacks
        self._run_callbacks(delivery, output)

        return output

    def _run_process_plugin(
        self, method: str, source: str, destination: str, metadata: dict, dry_run: bool
    ) -> bool:
        """
        Dynamically loads and executes a process plugin (copy, move, etc.).
        """
        try:
            # Dynamic import: kolett.plugins.process.{method}.plugin
            module_path = f"kolett.plugins.process.{method}.plugin"
            module = importlib.import_module(module_path)

            # Get plugin-specific config from global settings
            process_config = (
                self.config.get("plugins", {}).get("process", {}).get(method, {})
            )

            # Instantiate and run
            plugin_class = getattr(module, "Plugin")
            plugin_instance = plugin_class(process_config, dry_run=dry_run)
            return plugin_instance.run(source, destination, metadata)

        except Exception as e:
            logger.error(f"Process plugin {method} failed: {str(e)}")
            return False

    def _run_callbacks(self, delivery: DeliveryInput, output: DeliveryOutput):
        """
        Dynamically loads and executes callback plugins defined in the input.
        """
        if not hasattr(delivery, "callbacks") or not delivery.callbacks:
            # Fallback to notifications list for backward compatibility if needed
            return

        for plugin_name, plugin_config in delivery.callbacks.items():
            try:
                # Skip if the plugin is explicitly disabled in config
                if not plugin_config.get("enabled", True):
                    logger.info(f"Plugin {plugin_name} is disabled. Skipping.")
                    continue

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
