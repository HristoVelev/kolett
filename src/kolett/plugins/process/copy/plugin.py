import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Tuple

from jinja2 import Template

from kolett.plugins.base import ProcessPlugin

logger = logging.getLogger("kolett.plugins.process.copy")


class Plugin(ProcessPlugin):
    """
    Robust Copy Process Plugin for Kolett with Template support.
    Performs a file copy designed to handle filesystems (like NFS/JuiceFS)
    that may not support full metadata preservation (ENOTSUPP / 524).

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
                    f"Copy plugin template rendering failed: {e}. Falling back to engine destination."
                )
                dest_path = Path(destination)
        else:
            dest_path = Path(destination)

        if self.dry_run:
            logger.info(f"DRY RUN: Copying {src_path} -> {dest_path}")
            return True, str(dest_path)

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
            return True, str(dest_path)

        except Exception as e:
            logger.error(f"Failed to copy {source} to {dest_path}: {str(e)}")
            return False, str(dest_path)
