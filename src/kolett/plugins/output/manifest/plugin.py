import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from kolett.plugins.base import CallbackPlugin
from kolett.protocol import DeliveryOutput, ItemResult
from kolett.templating import render_manifest

logger = logging.getLogger("kolett.plugins.output.manifest")


class Plugin(CallbackPlugin):
    """
    Manifest Maker Output Plugin for Kolett.
    Generates a Markdown manifest in the delivery folder.
    Includes VFX sequence grouping logic to collapse frames into ranges.
    """

    def run(self, delivery_output: DeliveryOutput) -> bool:
        template_name = self.config.get("template_name", "manifest.md.j2")
        template_dir = self.config.get("template_dir")

        # Resolve template directory:
        # 1. Config override
        # 2. Default to the plugin's own directory
        if not template_dir:
            template_dir = str(Path(__file__).parent)

        manifest_file = Path(delivery_output.delivery_path) / "manifest.md"

        if self.dry_run:
            logger.info(f"DRY RUN: Manifest would be generated at {manifest_file}")
            return True

        try:
            # Group sequences for display
            grouped_results = self._group_sequences(delivery_output.results)

            # Prepare context for Jinja2
            context = {
                "package_name": delivery_output.package_name,
                "timestamp": delivery_output.timestamp,
                "delivery_path": delivery_output.delivery_path,
                "summary": delivery_output.summary,
                "results": grouped_results,
                "client_config": "standard",  # Can be enriched later
            }

            # Render manifest content
            content = render_manifest(template_name, template_dir, context)

            # Write to file
            with open(manifest_file, "w") as f:
                f.write(content)

            logger.info(f"Manifest successfully generated: {manifest_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate manifest: {str(e)}")
            return False

    def _group_sequences(self, results: List[ItemResult]) -> List[Dict[str, Any]]:
        """
        Groups individual frames in the results list into sequence strings for display.
        Example: shot.1001.exr, shot.1002.exr -> shot.[1001-1002].exr
        """
        # Regex to find frame numbers: name.1001.exr or name_1001.exr
        pattern = re.compile(r"^(.*?)[._](\d+)\.([a-zA-Z0-9]+)$")

        sequences = defaultdict(list)
        others = []

        for res in results:
            if not res.success:
                # Keep failed items separate
                others.append(
                    {
                        "source": res.source,
                        "destination": res.destination,
                        "description": res.description,
                        "success": False,
                        "error": res.error,
                    }
                )
                continue

            dest_path = Path(res.destination)
            match = pattern.match(dest_path.name)
            if match:
                prefix, frame, ext = match.groups()
                # Group by directory + prefix + extension
                key = (str(dest_path.parent), prefix, ext)
                sequences[key].append((int(frame), res))
            else:
                others.append(
                    {
                        "source": res.source,
                        "destination": res.destination,
                        "description": res.description,
                        "success": True,
                    }
                )

        final_results = []
        for (parent, prefix, ext), frames in sequences.items():
            if len(frames) > 1:
                frames.sort()
                start = frames[0][0]
                end = frames[-1][0]

                # Use the first frame's description for the sequence
                description = frames[0][1].description

                final_results.append(
                    {
                        "source": f"{prefix}.[{start}-{end}].{ext}",
                        "destination": f"{prefix}.[{start}-{end}].{ext}",
                        "description": description,
                        "success": True,
                    }
                )
            else:
                # Only one frame, don't treat as sequence
                res = frames[0][1]
                final_results.append(
                    {
                        "source": Path(res.source).name,
                        "destination": Path(res.destination).name,
                        "description": res.description,
                        "success": True,
                    }
                )

        return final_results + others
