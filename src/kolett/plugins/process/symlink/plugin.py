import logging
import os
from pathlib import Path
from typing import Any, Dict, Tuple

from jinja2 import Template

from kolett.plugins.base import ProcessPlugin

logger = logging.getLogger("kolett.plugins.process.symlink")


class Plugin(ProcessPlugin):
    """
    Symlink Process Plugin for Kolett with Template support.
    Creates a symbolic link at the destination pointing to the source.
    Useful for internal deliveries or saving storage space.

    Supports an optional 'target_template' in the plugin configuration to
    build the destination path using metadata.
    """

    def run(
        self, source: str, destination: str, metadata: Dict[str, Any]
    ) -> Tuple[bool, str]:
        src_path = Path(source)

        # 1. Determine the final destination path
        # If the plugin config has a target_template, it takes precedence for the filename
        template_str = self.config.get("target_template")
        if template_str:
            try:
                template = Template(template_str)
                rendered_filename = template.render(**metadata)
                # The engine already calculated the parent directory (package root + subfolders)
                # We replace the filename part of the engine-provided destination
                dest_path = Path(destination).parent / rendered_filename
            except Exception as e:
                logger.warning(
                    f"Symlink plugin template rendering failed: {e}. Falling back to engine destination."
                )
                dest_path = Path(destination)
        else:
            dest_path = Path(destination)

        if self.dry_run:
            logger.info(f"DRY RUN: Symlinking {src_path} -> {dest_path}")
            return True, str(dest_path)

        try:
            # Ensure the parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove destination if it already exists to avoid FileExistsError
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()

            # Create the symbolic link
            os.symlink(src_path, dest_path)

            logger.debug(f"Successfully symlinked {src_path.name} to {dest_path}")
            return True, str(dest_path)

        except Exception as e:
            logger.error(f"Failed to symlink {source} to {dest_path}: {str(e)}")
            return False, str(dest_path)
