import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from kolett.plugins.base import ProcessPlugin

logger = logging.getLogger("kolett.plugins.process.copy")


class Plugin(ProcessPlugin):
    """
    Standard Copy Process Plugin for Kolett.
    Performs a standard file copy using shutil.copy2 to preserve metadata.
    """

    def run(self, source: str, destination: str, metadata: Dict[str, Any]) -> bool:
        src_path = Path(source)
        dest_path = Path(destination)

        if self.dry_run:
            logger.info(f"DRY RUN: Copying {src_path} -> {dest_path}")
            return True

        try:
            # Ensure the parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Perform the copy
            # shutil.copy2 copies the file data and attempts to preserve metadata (mtime, etc.)
            shutil.copy2(src_path, dest_path)

            logger.debug(f"Successfully copied {src_path.name} to {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy {source} to {destination}: {str(e)}")
            return False
