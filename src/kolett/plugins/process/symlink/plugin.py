import logging
import os
from pathlib import Path
from typing import Any, Dict

from kolett.plugins.base import ProcessPlugin

logger = logging.getLogger("kolett.plugins.process.symlink")


class Plugin(ProcessPlugin):
    """
    Symlink Process Plugin for Kolett.
    Creates a symbolic link at the destination pointing to the source.
    Useful for internal deliveries or saving storage space.
    """

    def run(self, source: str, destination: str, metadata: Dict[str, Any]) -> bool:
        src_path = Path(source)
        dest_path = Path(destination)

        if self.dry_run:
            logger.info(f"DRY RUN: Symlinking {src_path} -> {dest_path}")
            return True

        try:
            # Ensure the parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove destination if it already exists to avoid FileExistsError
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()

            # Create the symbolic link
            os.symlink(src_path, dest_path)

            logger.debug(f"Successfully symlinked {src_path.name} to {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to symlink {source} to {destination}: {str(e)}")
            return False
