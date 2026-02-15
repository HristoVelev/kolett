import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from kolett.plugins.base import ProcessPlugin

logger = logging.getLogger("kolett.plugins.process.copy")


class Plugin(ProcessPlugin):
    """
    Robust Copy Process Plugin for Kolett.
    Performs a file copy designed to handle filesystems (like NFS/JuiceFS)
    that may not support full metadata preservation (ENOTSUPP / 524).
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

            # Use shutil.copy instead of copy2 to avoid metadata support issues
            # on NFS/JuiceFS. copy() preserves content and permissions but is
            # less aggressive about xattrs/flags which often cause Errno 524.
            shutil.copy(src_path, dest_path)

            # Try to preserve mtime separately as it's useful for VFX but non-critical
            try:
                stat = os.stat(src_path)
                os.utime(dest_path, (stat.st_atime, stat.st_mtime))
            except Exception:
                # Silently ignore if timestamp preservation fails
                pass

            logger.debug(f"Successfully copied {src_path.name} to {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy {source} to {destination}: {str(e)}")
            return False
